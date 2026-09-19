# Stream A: Core

Owns: websocket server, rooms, event log, `context_for`, routing whispers to the
right phone, replay, repo, HTTPS tunnel.

Scope: only edit files under `/server`. Do not edit `/contracts/*` — those are
frozen; propose changes to the other stream owners instead.

Talks to Brain (`/brain`) by calling its functions directly (in-process Python
import) using the signatures in `contracts/schema.py`. Talks to the client
(`/client`) only via the websocket message shapes in `contracts/README.md`.

Work alone by stubbing Brain with hardcoded whispers until the real one is ready.
