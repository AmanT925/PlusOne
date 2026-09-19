"""Multi-room hub: ingest events, run context_for, route whispers."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from contracts.schema import Event
from server import brain_adapter
from server.context import context_for, public_model_inputs
from server.linq import LinqClient
from server.media_store import media_store
from server.store import Store
from server import xai

log = logging.getLogger("plusone.rooms")


def public_base_url() -> str:
    return (os.environ.get("PLUSONE_PUBLIC_BASE_URL") or "").rstrip("/")


def media_public_url(token: str) -> str | None:
    base = public_base_url()
    if not base:
        return None
    return f"{base}/media/{token}"


class RoomHub:
    def __init__(self, store: Store, linq: LinqClient | None = None) -> None:
        self.store = store
        self.linq = linq or LinqClient()
        self._sockets: dict[str, dict[str, WebSocket]] = {}
        self._imagine_sent: set[str] = set()

    def default_room_id(self) -> str:
        return os.environ.get("PLUSONE_ROOM_ID", "demo")

    def _room_sockets(self, room_id: str) -> dict[str, WebSocket]:
        return self._sockets.setdefault(room_id, {})

    async def connect(self, room_id: str, user: str, websocket: WebSocket) -> None:
        await websocket.accept()
        sockets = self._room_sockets(room_id)
        previous = sockets.get(user)
        sockets[user] = websocket
        self.store.upsert_member(room_id, user)
        if previous is not None and previous is not websocket:
            try:
                await previous.close()
            except Exception:
                pass
        await self._replay_public(room_id, websocket)
        await self._broadcast_counter(room_id)

    def disconnect(self, room_id: str, user: str, websocket: WebSocket) -> None:
        sockets = self._room_sockets(room_id)
        if sockets.get(user) is websocket:
            sockets.pop(user, None)

    async def _replay_public(self, room_id: str, websocket: WebSocket) -> None:
        """Replay public history. Private text stays off the wire."""
        try:
            for event in self.store.events(room_id):
                if event.visibility == "public":
                    await websocket.send_json(
                        {"type": "public", "speaker": event.speaker, "text": event.text}
                    )
        except Exception:
            log.exception("replay failed")

    async def ingest(
        self,
        room_id: str,
        speaker: str,
        visibility: str,
        text: str,
        *,
        ts: float | None = None,
    ) -> Event:
        ts = time.time() if ts is None else ts
        self.store.upsert_member(room_id, speaker)
        event = self.store.append_event(room_id, ts, speaker, visibility, text)

        extracted = brain_adapter.extract_constraints(event)
        if extracted:
            self.store.add_constraints(room_id, event.id, extracted)

        if event.visibility == "public":
            await self._broadcast(
                room_id,
                {"type": "public", "speaker": event.speaker, "text": event.text},
            )
            await self._maybe_whisper_all(room_id, trigger="public", now=ts)
        else:
            viewer = event.visibility.split(":", 1)[-1] if ":" in event.visibility else speaker
            await self._maybe_whisper(room_id, viewer, trigger="private", now=ts)

        await self._broadcast_counter(room_id)
        return event

    async def _maybe_whisper_all(self, room_id: str, trigger: str, now: float) -> None:
        for user in self._known_users(room_id):
            await self._maybe_whisper(room_id, user, trigger=trigger, now=now)

    async def _maybe_whisper(self, room_id: str, viewer: str, trigger: str, now: float) -> None:
        events = self.store.events(room_id)
        constraints = self.store.constraints(room_id)
        has_private = any(e.visibility == f"private:{viewer}" for e in events)
        last_public = next((e.text for e in reversed(events) if e.visibility == "public"), "")
        viewer_constraints = [c for c in constraints if c.user == viewer]
        state = {
            "viewer": viewer,
            "now": now,
            "last_whisper_at": self.store.last_whisper_at(room_id, viewer),
            "has_private": has_private,
            "trigger": trigger,
            "mid_sentence": False,
            "public_proposal": last_public,
            "viewer_constraints": viewer_constraints,
        }
        if not brain_adapter.should_whisper(state):
            return

        ctx = context_for(viewer, events, constraints, brain_adapter.group_summary)
        # Public speech never receives this ctx; write_whisper only sees context_for output.
        text = brain_adapter.write_whisper(ctx)
        self.store.set_whisper_at(room_id, viewer, now)
        await self._deliver_whisper(room_id, viewer, text)

    async def maybe_public_suggestion(self, room_id: str, text: str) -> None:
        """Send a table-safe line to the group thread and websocket clients."""
        events = self.store.events(room_id)
        constraints = self.store.constraints(room_id)
        _public_log, summary = public_model_inputs(
            events, constraints, brain_adapter.group_summary
        )
        # Guardrail: the suggestion we send is authored here from public+summary only.
        payload = {"type": "public", "speaker": "plus-one", "text": text}
        await self._broadcast(room_id, payload)
        group_chat = self.store.group_chat_for(room_id)
        if group_chat and self.linq:
            await self.linq.start_typing(group_chat)
            await self.linq.send_text(text, chat_id=group_chat)
        _ = summary

    async def _deliver_whisper(self, room_id: str, viewer: str, text: str) -> None:
        audio_url, audio_bytes, tts_ok = await self._try_tts(text)
        payload: dict[str, Any] = {"type": "whisper", "text": text}
        if audio_url:
            # Optional field for Expo playback (contracts still require text).
            payload["audio_url"] = audio_url

        socket = self._room_sockets(room_id).get(viewer)
        if socket is not None:
            await self._send(room_id, viewer, socket, payload)

        chat_id = self.store.dm_chat_for(room_id, viewer)
        phone = self.store.phone_for(room_id, viewer)
        if self.linq and (chat_id or phone):
            if chat_id:
                await self.linq.start_typing(chat_id)
            await self.linq.send_text(text, chat_id=chat_id, to=phone if not chat_id else None)
            if audio_bytes and chat_id:
                await self._send_linq_voice_memo(chat_id, audio_bytes)
            elif not tts_ok and xai.voice_enabled() and chat_id:
                # TTS timed out or failed before bytes; finish in background for Linq.
                asyncio.create_task(self._late_voice_memo(chat_id, text))

        if not tts_ok:
            await self._imagine_fallback(room_id)

    async def _try_tts(self, text: str) -> tuple[str | None, bytes | None, bool]:
        """Return (audio_url, audio_bytes, ok). ok=False triggers Imagine fallback."""
        if not xai.voice_enabled():
            return None, None, False
        budget = float(os.environ.get("PLUSONE_TTS_BUDGET_SEC", "2.8"))
        try:
            audio = await asyncio.wait_for(xai.synthesize_speech(text), timeout=budget)
        except Exception:
            log.exception("Grok Voice TTS failed or timed out")
            return None, None, False
        token = media_store.put(audio, "audio/mpeg")
        url = media_public_url(token) or f"/media/{token}"
        return url, audio, True

    async def _send_linq_voice_memo(self, chat_id: str, audio: bytes) -> bool:
        uploaded = await self.linq.upload_attachment(
            audio, filename="plusone-whisper.mp3", content_type="audio/mpeg"
        )
        if not uploaded:
            return False
        return await self.linq.send_voice_memo(
            chat_id=chat_id, attachment_id=uploaded["attachment_id"]
        )

    async def _late_voice_memo(self, chat_id: str, text: str) -> None:
        try:
            audio = await xai.synthesize_speech(text)
            await self._send_linq_voice_memo(chat_id, audio)
        except Exception:
            log.exception("late Linq voice memo failed")

    async def _imagine_fallback(self, room_id: str) -> None:
        """If Voice is blocked/unavailable, still use Imagine once for SpaceXAI."""
        if not xai.imagine_enabled():
            return
        if room_id in self._imagine_sent:
            return
        events = self.store.events(room_id)
        last_public = next((e.text for e in reversed(events) if e.visibility == "public"), "")
        group_chat = self.store.group_chat_for(room_id)
        if not group_chat or not self.linq:
            log.info("Imagine fallback skipped (no group chat bound yet)")
            return
        try:
            result = await xai.generate_image(xai.trip_still_prompt(last_public))
            ok = await self.linq.send_media(
                chat_id=group_chat,
                media_url=result["url"],
                caption="Trip vibe (Grok Imagine) — text whispers still apply privately.",
            )
            if ok:
                self._imagine_sent.add(room_id)
        except Exception:
            log.exception("Grok Imagine fallback failed")
    def _known_users(self, room_id: str) -> set[str]:
        users = set(self.store.members(room_id))
        users.update(self._room_sockets(room_id).keys())
        return users

    def _counter_payload(self, room_id: str) -> dict[str, Any]:
        events = self.store.events(room_id)
        shared = {e.speaker for e in events if e.visibility != "public"}
        total = len(self._known_users(room_id))
        return {"type": "counter", "shared": len(shared), "total": total}

    async def _broadcast_counter(self, room_id: str) -> None:
        await self._broadcast(room_id, self._counter_payload(room_id))

    async def _broadcast(self, room_id: str, payload: dict[str, Any]) -> None:
        sockets = list(self._room_sockets(room_id).items())
        for user, ws in sockets:
            await self._send(room_id, user, ws, payload)

    async def _send(
        self, room_id: str, user: str, websocket: WebSocket, payload: dict[str, Any]
    ) -> None:
        try:
            await websocket.send_json(payload)
        except Exception:
            log.info("dropping dead websocket for %s in %s", user, room_id)
            self.disconnect(room_id, user, websocket)


async def websocket_loop(hub: RoomHub, room_id: str, user: str, websocket: WebSocket) -> None:
    await hub.connect(room_id, user, websocket)
    try:
        while True:
            msg = await websocket.receive_json()
            if msg.get("type") not in (None, "utterance"):
                continue
            visibility = msg.get("visibility") or "public"
            text = msg.get("text") or ""
            if not text:
                continue
            if visibility.startswith("private:") and visibility != f"private:{user}":
                visibility = f"private:{user}"
            elif visibility != "public" and not visibility.startswith("private:"):
                visibility = f"private:{user}"
            await hub.ingest(room_id, user, visibility, text)
    except WebSocketDisconnect:
        hub.disconnect(room_id, user, websocket)
    except Exception:
        log.exception("websocket error for %s in %s", user, room_id)
        hub.disconnect(room_id, user, websocket)
        try:
            await websocket.close()
        except Exception:
            pass
