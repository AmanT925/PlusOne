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

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket
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


@app.get("/health")
async def health():
    return {"ok": True, "linq": bool(linq_api_key())}


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
