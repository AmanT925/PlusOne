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
from server.store import Store

log = logging.getLogger("plusone.rooms")


class RoomHub:
    def __init__(self, store: Store, linq: LinqClient | None = None) -> None:
        self.store = store
        self.linq = linq or LinqClient()
        self._sockets: dict[str, dict[str, WebSocket]] = {}
        self._last_public_at: dict[str, float] = {}
        self._last_public_proposal: dict[str, str] = {}
        self._imagine_done: set[str] = set()

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
            # Public suggestion first: webhook timeouts used to kill ingest during LLM whispers.
            posted = False
            if brain_adapter.looks_like_proposal(event.text):
                posted = await self._maybe_public_plan(room_id, event.text, now=ts)
            if not posted:
                await self._maybe_whisper_all(room_id, trigger="public", now=ts)
        else:
            viewer = event.visibility.split(":", 1)[-1] if ":" in event.visibility else speaker
            if brain_adapter.looks_like_proposal(event.text):
                await self._maybe_public_plan(
                    room_id, event.text, now=ts, fallback_user=viewer
                )
            else:
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

    async def _maybe_public_plan(
        self,
        room_id: str,
        proposal: str,
        now: float,
        fallback_user: str | None = None,
    ) -> bool:
        key = " ".join(proposal.lower().split())[:120]
        last_at = self._last_public_at.get(room_id)
        last_key = self._last_public_proposal.get(room_id)
        if last_at is not None and now - last_at < 20 and last_key == key:
            return True
        constraints = self.store.constraints(room_id)
        text = brain_adapter.suggest_public(proposal, constraints)
        if not text:
            log.info("no public suggestion for %r (%s constraints)", proposal[:80], len(constraints))
            return False
        self._last_public_at[room_id] = now
        self._last_public_proposal[room_id] = key
        await self.maybe_public_suggestion(room_id, text, fallback_user=fallback_user)
        return True

    async def maybe_public_suggestion(
        self, room_id: str, text: str, fallback_user: str | None = None
    ) -> None:
        """Send a table-safe line to the group thread (or the proposer's DM)."""
        events = self.store.events(room_id)
        constraints = self.store.constraints(room_id)
        _public_log, summary = public_model_inputs(
            events, constraints, brain_adapter.group_summary
        )
        # Guardrail: the suggestion we send is authored here from public+summary only.
        payload = {"type": "public", "speaker": "plus-one", "text": text}
        await self._broadcast(room_id, payload)
        self.store.append_event(room_id, time.time(), "plus-one", "public", text)
        sent = False
        group_chat = self.store.group_chat_for(room_id)
        if group_chat and self.linq:
            await self.linq.start_typing(group_chat)
            sent = await self.linq.send_text(text, chat_id=group_chat)
            if sent:
                log.info("public suggestion sent to group %s", group_chat)
                imagine = os.environ.get("PLUSONE_IMAGINE", "1").strip().lower()
                if imagine not in ("0", "false", "no", "off"):
                    asyncio.create_task(self._maybe_imagine(room_id, group_chat, text))
        if not sent and self.linq:
            targets: list[str] = []
            if fallback_user:
                targets.append(fallback_user)
            else:
                targets.extend(self._known_users(room_id))
            dm_ok = False
            for user in targets:
                chat_id = self.store.dm_chat_for(room_id, user)
                phone = self.store.phone_for(room_id, user)
                if not (chat_id or phone):
                    continue
                if chat_id:
                    await self.linq.start_typing(chat_id)
                ok = await self.linq.send_text(
                    text, chat_id=chat_id, to=phone if not chat_id else None
                )
                dm_ok = dm_ok or ok
            if dm_ok:
                log.info("public suggestion sent via DM fallback")
            else:
                log.warning("public suggestion not delivered over Linq")
        _ = summary

    async def _maybe_imagine(self, room_id: str, group_chat: str, suggestion: str) -> None:
        if room_id in self._imagine_done:
            return
        if os.environ.get("PLUSONE_IMAGINE", "1").strip().lower() in ("0", "false", "no", "off"):
            return
        try:
            from server.xai_media import imagine_still

            url = await imagine_still(
                "Photoreal still of friends on a casual local hang, picnic or mid-range dinner, "
                "warm evening light, no text, no logos, no readable signs."
            )
        except Exception:
            log.exception("imagine failed")
            return
        if not url or not self.linq:
            return
        self._imagine_done.add(room_id)
        await self.linq.send_link(url, chat_id=group_chat)
        _ = suggestion

    async def _deliver_whisper(self, room_id: str, viewer: str, text: str) -> None:
        payload = {"type": "whisper", "text": text}
        socket = self._room_sockets(room_id).get(viewer)
        if socket is not None:
            await self._send(room_id, viewer, socket, payload)
        chat_id = self.store.dm_chat_for(room_id, viewer)
        phone = self.store.phone_for(room_id, viewer)
        if self.linq and (chat_id or phone):
            if chat_id:
                await self.linq.start_typing(chat_id)
            await self.linq.send_text(text, chat_id=chat_id, to=phone if not chat_id else None)

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
