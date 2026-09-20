# Plus One Core (`/server`)

Websocket + Linq adapter. Scope is this folder only; `/contracts` is frozen.

## Run

From the repo root (so `contracts` and `brain` import):

```bash
pip install -r server/requirements.txt
python -m server
```

SQLite log defaults to `server/plusone.db`. Override with `PLUSONE_DB`.

## Websocket (stream C)

- Default room: `ws://HOST/ws/{user}`
- Named room: `ws://HOST/ws/{room_id}/{user}`

Reconnects replace the previous socket for that user and replay public history plus the current `counter`. Client message shapes stay as in `contracts/README.md`.

## HTTP helpers (no Linq key yet)

```bash
curl -X POST http://localhost:8000/rooms/demo/utterances \
  -H "content-type: application/json" \
  -d "{\"speaker\":\"sam\",\"visibility\":\"private:sam\",\"text\":\"I can't do more than $150\"}"

curl http://localhost:8000/rooms/demo/events
```

## Linq

Env:

| Variable | Purpose |
|---|---|
| `LINQ_API_KEY` | Partner API bearer token |
| `LINQ_WEBHOOK_SECRET` | `whsec_...` from the webhook subscription |
| `LINQ_SKIP_VERIFY` | `1` only for local unsigned tests |
| `PLUSONE_ROOM_ID` | Room inbound chats join (default `demo`) |
| `PLUSONE_HANDLES` | `sam:+15551111111,priya:+15552222222` so iMessage phones match websocket names |

Subscribe Linq to:

`https://YOUR_TUNNEL/linq/webhook?version=2026-02-03`

Events: `message.received` (minimum). Mapping: 1:1 inbound → `private:<user>`, group inbound → `public`. Whispers go back to that person's 1:1 chat (typing indicator while Brain runs). Public suggestions go to the group chat.

## HTTPS tunnel (phones + Linq webhooks)

Linq requires HTTPS. From another terminal, pick one:

```bash
cloudflared tunnel --url http://localhost:8000
```

```bash
ngrok http 8000
```

Put the printed `https://...` URL into the Linq webhook subscription. Leave uvicorn running.

## Brain

`server/brain_adapter.py` imports `brain.brain` in-process. If those functions still raise `NotImplementedError`, Core uses local stubs. `context_for` always runs before `write_whisper`.
