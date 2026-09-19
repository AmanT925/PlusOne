"""Stream A: Core — websocket server, rooms, event log, context_for, Linq.

Build-order step 1 (SPEC.md): two people text Plus One through Linq (a private
thread each, plus a group thread), messages tagged public/private, whisper
routed back to the right private thread. Brain is called in-process and stubbed
when stream B still raises NotImplementedError.
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from server.envload import load_plusone_env, linq_api_key

from server.linq import (
    LinqClient,
    parse_handle_map,
    parse_inbound,
    user_from_handle,
    verify_signature,
    visibility_for,
)
from server.media_store import media_store
from server.rooms import RoomHub, websocket_loop
from server.store import Store
from server import stt, xai
from server.wavutil import pcm16_to_wav

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


@app.get("/health")
async def health():
    return {
        "ok": True,
        "linq": bool(linq_api_key()),
        "xai": bool(xai.xai_api_key()),
        "voice": xai.voice_enabled(),
        "imagine": xai.imagine_enabled(),
        "stt": stt.stt_enabled(),
    }


@app.get("/media/{token}")
async def get_media(token: str):
    item = media_store.get(token)
    if item is None:
        raise HTTPException(404, "media expired or unknown")
    return Response(content=item.data, media_type=item.content_type)


@app.post("/demo/sponsors/voice")
async def demo_voice(body: dict | None = None):
    """One-shot Grok Voice call for the SpaceXAI demo path (screenshot + working call)."""
    body = body or {}
    text = (body.get("text") or "Plus One whisper: keep the weekend under one-fifty.").strip()
    if not xai.xai_api_key():
        raise HTTPException(503, "XAI_API_KEY is not set")
    try:
        audio = await xai.synthesize_speech(text)
    except Exception as exc:
        raise HTTPException(502, f"TTS failed: {exc}") from exc
    token = media_store.put(audio, "audio/mpeg")
    return {
        "ok": True,
        "bytes": len(audio),
        "media_path": f"/media/{token}",
        "voice_id": body.get("voice_id") or "eve",
        "text": text,
    }


@app.post("/demo/sponsors/imagine")
async def demo_imagine(body: dict | None = None):
    """One-shot Grok Imagine still for SpaceXAI if Voice is blocked."""
    body = body or {}
    prompt = (body.get("prompt") or xai.trip_still_prompt(body.get("proposal") or "")).strip()
    if not xai.xai_api_key():
        raise HTTPException(503, "XAI_API_KEY is not set")
    try:
        result = await xai.generate_image(prompt)
    except Exception as exc:
        raise HTTPException(502, f"Imagine failed: {exc}") from exc
    return {"ok": True, **result, "prompt": prompt}


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


@app.post("/rooms/{room_id}/audio")
async def post_audio_utterance(
    room_id: str,
    speaker: str = Form(...),
    visibility: str = Form("public"),
    transcript: str | None = Form(None),
    sample_rate: int = Form(16000),
    audio: UploadFile = File(...),
):
    """Korvo / hold-to-talk: upload WAV (or raw PCM16) → STT → same ingest as text.

    Dev bypass: set form field `transcript` to skip Muse (firmware Phase 1–2).
    Raw PCM: Content-Type audio/L16 or filename ending in .pcm / .raw.
    """
    speaker = speaker.strip()
    if not speaker:
        raise HTTPException(400, "speaker is required")
    raw = await audio.read()
    if not raw:
        raise HTTPException(400, "empty audio")

    text = (transcript or "").strip()
    stt_route = "bypass"
    if not text:
        content_type = (audio.content_type or "").lower()
        name = (audio.filename or "").lower()
        is_pcm = (
            "audio/l16" in content_type
            or "pcm" in content_type
            or name.endswith(".pcm")
            or name.endswith(".raw")
        )
        wav = raw if raw[:4] == b"RIFF" else (pcm16_to_wav(raw, sample_rate=sample_rate) if is_pcm else raw)
        if wav[:4] != b"RIFF":
            # Assume PCM16 if not already WAV
            wav = pcm16_to_wav(raw, sample_rate=sample_rate)
        try:
            text = await stt.transcribe_wav(wav)
            stt_route = "muse"
        except Exception as exc:
            raise HTTPException(502, f"STT failed: {exc}") from exc
    if not text:
        raise HTTPException(400, "no transcript")

    if visibility.startswith("private:") and visibility != f"private:{speaker}":
        visibility = f"private:{speaker}"
    elif visibility != "public" and not visibility.startswith("private:"):
        visibility = f"private:{speaker}"

    event = await hub().ingest(room_id, speaker, visibility, text)
    return {
        "id": event.id,
        "visibility": event.visibility,
        "text": text,
        "stt": stt_route,
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
