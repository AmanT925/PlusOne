"""Stream A: Core — websocket server, rooms, event log, context_for, Linq.

Build-order step 1 (SPEC.md): two people text Plus One through Linq (a private
thread each, plus a group thread), messages tagged public/private, whisper
routed back to the right private thread. Brain is called in-process and stubbed
when stream B still raises NotImplementedError.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from server.envload import load_plusone_env, linq_api_key

from server.linq import (
    LinqClient,
    parse_handle_map,
    parse_inbound,
    user_from_handle,
    verify_signature,
    visibility_for,
)
from server.rooms import RoomHub, websocket_loop
from server.store import Store

load_plusone_env()

log = logging.getLogger("plusone")
logging.basicConfig(level=logging.INFO)

DEFAULT_ROOM = os.environ.get("PLUSONE_ROOM_ID", "demo")


def _db_path() -> str:
    return os.environ.get("PLUSONE_DB", str(Path(__file__).resolve().parent / "plusone.db"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = Store(_db_path())
    linq = LinqClient()
    app.state.store = store
    app.state.linq = linq
    app.state.hub = RoomHub(store, linq)
    app.state.handle_map = parse_handle_map()
    try:
        yield
    finally:
        await linq.aclose()
        store.close()


app = FastAPI(title="Plus One Core", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def hub() -> RoomHub:
    return app.state.hub


_fixture_leaks: dict | None = None


def _fixture_leak_summary() -> dict:
    """Cached, template-only. Never call Muse/Grok on the poll path."""
    global _fixture_leaks
    if _fixture_leaks is not None:
        return _fixture_leaks
    from brain.leak_test import run as fixture_run

    prev = os.environ.get("PLUSONE_LLM")
    os.environ["PLUSONE_LLM"] = "0"
    try:
        result = fixture_run()
        _fixture_leaks = {"attempts": result["attempts"], "leaks": result["leaks"]}
    finally:
        if prev is None:
            os.environ.pop("PLUSONE_LLM", None)
        else:
            os.environ["PLUSONE_LLM"] = prev
    return _fixture_leaks


@app.get("/health")
async def health():
    from server.stt import stt_enabled

    return {
        "ok": True,
        "linq": bool(linq_api_key()),
        "xai": bool(os.environ.get("XAI_API_KEY", "").strip()),
        "stt": stt_enabled(),
    }


@app.get("/rooms/{room_id}/media")
async def room_media(room_id: str):
    return {"imagine_url": hub().imagine_url(room_id)}


@app.get("/rooms/{room_id}/users/{user}/whisper.mp3")
async def whisper_audio(room_id: str, user: str):
    from fastapi.responses import Response

    data = hub().whisper_mp3(room_id, user)
    if not data:
        raise HTTPException(404, "no whisper audio yet")
    return Response(
        content=data,
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/rooms/{room_id}/events")
async def list_events(room_id: str):
    """Replay helper: inspect the append-only log (includes private events)."""
    events = app.state.store.events(room_id)
    return [
        {
            "id": e.id,
            "ts": e.ts,
            "speaker": e.speaker,
            "visibility": e.visibility,
            "text": e.text,
        }
        for e in events
    ]


@app.post("/rooms/{room_id}/audio")
async def post_audio(
    room_id: str,
    speaker: str = Form(...),
    visibility: str = Form("public"),
    transcript: str | None = Form(None),
    audio: UploadFile = File(...),
):
    """Hold-to-talk: Muse STT then the same ingest path as typed utterances."""
    speaker = speaker.strip()
    if not speaker:
        raise HTTPException(400, "speaker is required")
    blob = await audio.read(10 * 1024 * 1024 + 1)
    if len(blob) > 10 * 1024 * 1024:
        raise HTTPException(413, "Recording is too large. Keep it under 60 seconds.")
    if not blob:
        raise HTTPException(400, "audio is required")

    text = (transcript or "").strip()
    stt_mode = "bypass"
    if not text:
        from server.stt import stt_enabled, transcribe_wav
        from server.audio_decode import muse_wav
        from starlette.concurrency import run_in_threadpool
        if not stt_enabled():
            raise HTTPException(
                503, "STT unavailable (no Muse key); pass transcript bypass"
            )
        try:
            wav = await run_in_threadpool(muse_wav, blob, audio.filename or "")
        except ValueError:
            raise HTTPException(400, "Invalid or too-long recording. Record a new clip under 60 seconds.")
        try:
            text = await transcribe_wav(wav)
        except Exception as exc:
            log.warning("stt failed: %s", exc)
            raise HTTPException(502, "STT failed") from exc
        stt_mode = "muse"

    if not text:
        raise HTTPException(400, "empty transcript")
    if not visibility:
        visibility = "public"
    if visibility.startswith("private:") and visibility != f"private:{speaker}":
        visibility = f"private:{speaker}"
    elif visibility != "public" and not visibility.startswith("private:"):
        visibility = f"private:{speaker}"

    event = await hub().ingest(room_id, speaker, visibility, text)
    return {
        "id": event.id,
        "visibility": event.visibility,
        "text": text,
        "stt": stt_mode,
    }


@app.post("/rooms/{room_id}/utterances")
async def post_utterance(room_id: str, body: dict):
    """HTTP stand-in for a typed message (useful before Linq keys land)."""
    speaker = body.get("speaker") or body.get("user")
    text = body.get("text") or ""
    visibility = body.get("visibility")
    if not speaker or not text:
        raise HTTPException(400, "speaker and text are required")
    if not visibility:
        visibility = "public"
    event = await hub().ingest(room_id, speaker, visibility, text)
    return {"id": event.id, "visibility": event.visibility}


@app.get("/rooms/{room_id}/leaks")
async def room_leaks(room_id: str):
    """Laptop judge screen: attempts vs leaks on this room + fixture harness."""
    from brain.leak_test import scan_events

    events = app.state.store.events(room_id)
    constraints = app.state.store.constraints(room_id)
    live = await asyncio.to_thread(scan_events, events, constraints)
    fixtures = await asyncio.to_thread(_fixture_leak_summary)
    return {
        "room": live,
        "fixtures": fixtures,
    }


@app.websocket("/ws/{user}")
async def ws_default_room(websocket: WebSocket, user: str):
    await websocket_loop(hub(), DEFAULT_ROOM, user, websocket)


@app.websocket("/ws/{room_id}/{user}")
async def ws_named_room(websocket: WebSocket, room_id: str, user: str):
    await websocket_loop(hub(), room_id, user, websocket)


@app.post("/linq/webhook")
async def linq_webhook(
    request: Request,
    webhook_id: str | None = Header(default=None, alias="webhook-id"),
    webhook_timestamp: str | None = Header(default=None, alias="webhook-timestamp"),
    webhook_signature: str | None = Header(default=None, alias="webhook-signature"),
):
    raw = await request.body()
    secret = os.environ.get("LINQ_WEBHOOK_SECRET", "")
    skip = os.environ.get("LINQ_SKIP_VERIFY", "").lower() in ("1", "true", "yes")
    if secret and not skip:
        headers = {
            "webhook-id": webhook_id or "",
            "webhook-timestamp": webhook_timestamp or "",
            "webhook-signature": webhook_signature or "",
        }
        if not verify_signature(secret, raw, headers):
            raise HTTPException(401, "invalid webhook signature")
    elif not skip:
        log.warning("LINQ_WEBHOOK_SECRET unset; rejecting webhook (set LINQ_SKIP_VERIFY=1 for local tests)")
        raise HTTPException(401, "webhook verification not configured")

    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)

    inbound = parse_inbound(payload)
    if inbound is None:
        return {"ok": True, "ignored": True}

    store = app.state.store
    if store.already_processed(inbound.event_id):
        return {"ok": True, "duplicate": True}

    room_id = os.environ.get("PLUSONE_ROOM_ID", DEFAULT_ROOM)
    handle_map: dict[str, str] = app.state.handle_map
    user = user_from_handle(inbound.speaker_handle, handle_map)

    existing = store.chat(inbound.chat_id)
    if existing is not None:
        room_id = existing["room_id"]
        if existing["kind"] == "dm" and existing["user"]:
            user = existing["user"]
    else:
        kind = "group" if inbound.is_group else "dm"
        store.bind_chat(inbound.chat_id, room_id, kind, None if inbound.is_group else user)

    if inbound.is_group:
        store.bind_chat(inbound.chat_id, room_id, "group", None)
        visibility = "public"
    else:
        store.bind_chat(inbound.chat_id, room_id, "dm", user)
        store.upsert_member(room_id, user, phone=inbound.speaker_handle)
        visibility = visibility_for(inbound, user)

    event = await hub().ingest(room_id, user, visibility, inbound.text)
    store.mark_processed(inbound.event_id)
    return {"ok": True, "event_id": event.id, "visibility": event.visibility, "room": room_id}


@app.get("/")
async def root():
    return PlainTextResponse(
        "Plus One Core. WS /ws/{user} or /ws/{room}/{user}. Linq POST /linq/webhook.\n"
    )
