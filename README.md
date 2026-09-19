# Plus One

Voice agent for group planning. See [SPEC.md](SPEC.md) for the full team plan
(concept, sponsor fit, architecture, build order, roles, demo script).

## Stack

- **Server** (`/server`, stream A: Core) — Python, FastAPI, websockets, plus a Linq adapter for iMessage/RCS/SMS webhooks
- **Brain** (`/brain`, stream B) — Python, plain functions, no server dependency
- **Client** (`/client`, stream C) — Expo (React Native), for the in-person earbud-audio channel and a text fallback
- **Contracts** (`/contracts`) — frozen shapes shared by all three streams
- **Fixtures** (`/fixtures`) — sample groups and canned whispers for offline dev

Plus One runs on two channels over one brain: iMessage (via [Linq](https://linqapp.com/imessage-api)) is the everyday, no-install channel — a private thread per person plus one group thread — and earbud audio (the Expo app) is the in-person channel. Both feed the same event log and the same `context_for(viewer)` privacy boundary. See `SPEC.md` for the full picture.

## Running the server

```bash
cd server
pip install -r requirements.txt
cd ..
uvicorn server.main:app --reload
```

## Running the client

```bash
cd client
npm start
```

## Repo layout

Each stream works only inside its own folder — see the `AGENTS.md` in each one
for scope and what not to touch. `/contracts` is frozen; changing it needs all
three stream owners to agree.
