# Plus One

Voice agent for group planning. See [SPEC.md](SPEC.md) for the full team plan
(concept, sponsor fit, architecture, build order, roles, demo script).

## Stack

- **Server** (`/server`, stream A: Core) — Python, FastAPI, websockets
- **Brain** (`/brain`, stream B) — Python, plain functions, no server dependency
- **Client** (`/client`, stream C) — Expo (React Native)
- **Contracts** (`/contracts`) — frozen shapes shared by all three streams
- **Fixtures** (`/fixtures`) — sample groups and canned whispers for offline dev

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
