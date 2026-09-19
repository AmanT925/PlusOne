# Stream A: Core

Owns: websocket server, rooms, event log, `context_for`, Linq adapter (webhooks
in, messages out), routing whispers to the right thread or phone, replay, repo,
HTTPS tunnel.

Scope: only edit files under `/server`. Do not edit `/contracts/*` — those are
frozen; propose changes to the other stream owners instead.

Talks to Brain (`/brain`) by calling its functions directly (in-process Python
import) using the signatures in `contracts/schema.py`. Talks to the client
(`/client`) via the websocket message shapes in `contracts/README.md`, and to
Linq via the mapping documented in that same file (inbound webhook -> `Event`,
whisper -> one-on-one thread, public suggestion -> group thread).

Work alone by stubbing Brain with hardcoded whispers until the real one is ready.
