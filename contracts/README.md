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

## Linq mapping (stream A)

Plus One also runs over iMessage/RCS/SMS via Linq, feeding the same event log
as the websocket channel above:

- An inbound message in a person's one-on-one thread becomes an `Event` with
  `visibility: "private:<user>"`.
- An inbound message in the group thread becomes a public `Event`.
- A whisper is sent back to that person's one-on-one thread.
- Public suggestions are sent to the group thread.

Leak testing must cover extraction attempts through the group thread, not only
the private one-on-one threads.
