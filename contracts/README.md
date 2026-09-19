# Contracts

These are frozen per `SPEC.md`'s "Contracts" section. Changing anything here needs
all three stream owners (A: Core, B: Brain, C: Voice/client) to agree.

- `schema.py` — shared Python types for `Event` and `Constraint`, and the function
  signatures stream B (Brain) exposes to stream A (Core). Both `/server` and `/brain`
  import from here instead of redefining these shapes.
- Websocket message shapes (client &lt;-&gt; server) are plain JSON and documented below,
  since the client is vanilla JS, not Python.

## Client to server

```json
{"type": "utterance", "visibility": "public", "text": "..."}
{"type": "utterance", "visibility": "private:<user>", "text": "..."}
```

## Server to client

```json
{"type": "whisper", "text": "..."}
{"type": "public", "speaker": "...", "text": "..."}
{"type": "counter", "shared": 0, "total": 0}
```
