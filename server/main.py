"""Stream A: Core — websocket server, rooms, event log, context_for.

Build order step 1 (see SPEC.md): two phones connected to one server, typed
messages tagged public or private, event log working. Brain (stream B) is
stubbed with hardcoded whispers until /brain is ready.
"""

import itertools
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from contracts.schema import Event

app = FastAPI()

# In-memory state for one room. Swap for SQLite later if we need replay across
# server restarts (see SPEC.md "Stack").
event_log: list[Event] = []
event_ids = itertools.count(1)
connections: dict[str, WebSocket] = {}


def stub_write_whisper(viewer: str) -> str:
    """Stand-in for brain.write_whisper until stream B's real one lands."""
    return f"(stub whisper for {viewer})"


@app.websocket("/ws/{user}")
async def room(websocket: WebSocket, user: str):
    await websocket.accept()
    connections[user] = websocket
    try:
        while True:
            msg = await websocket.receive_json()
            event = Event(
                id=next(event_ids),
                ts=time.time(),
                speaker=user,
                visibility=msg["visibility"],
                text=msg["text"],
            )
            event_log.append(event)

            if event.visibility == "public":
                for other in connections.values():
                    await other.send_json(
                        {"type": "public", "speaker": event.speaker, "text": event.text}
                    )
            else:
                whisper = stub_write_whisper(user)
                await websocket.send_json({"type": "whisper", "text": whisper})

            shared = len({e.speaker for e in event_log if e.visibility != "public"})
            for other in connections.values():
                await other.send_json(
                    {"type": "counter", "shared": shared, "total": len(connections)}
                )
    except WebSocketDisconnect:
        connections.pop(user, None)
