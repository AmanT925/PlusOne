# Part 1: Core (`/server`)

Branch: `part-1-core`. See `PARTS.md` on `main` for how the 3 parts fit
together, and `server/AGENTS.md` for scope rules (only edit `/server`, don't
touch `/contracts`). Full context: `SPEC.md`.

You own the websocket server, the event log, the privacy-boundary function,
the Linq (iMessage/RCS/SMS) adapter, and routing whispers to the right thread
or phone. Stream B (Brain) and stream C (client) both talk to you through the
frozen shapes in `contracts/schema.py` and `contracts/README.md` — don't wait
on them; stub Brain with hardcoded whispers and test against `contracts/`
directly.

## Checklist

- [ ] **Linq adapter** — receive inbound webhooks (private thread -> `Event` with `visibility: "private:<user>"`, group thread -> public `Event`) and send outbound messages (whisper -> one-on-one thread, public suggestion -> group thread). Mapping is documented in `contracts/README.md`.
- [ ] Get a Linq API key and phone number; confirm webhook delivery end to end
- [ ] `context_for(viewer)` — the actual privacy-boundary function from `SPEC.md`. `main.py` currently stubs the whisper text directly instead of building per-viewer context; this is the most important item, it's the project's originality claim
- [ ] Wire real `brain.py` functions (stream B) into the server in place of `stub_write_whisper`
- [ ] Multi-room support — `main.py` currently assumes one global room/event log
- [ ] Persist the event log to SQLite for replay (currently in-memory only)
- [ ] HTTPS tunnel so phones and Linq webhooks can reach the server during dev and demo (e.g. ngrok/cloudflared)
- [ ] Reconnect handling for dropped websockets (currently a bare `except WebSocketDisconnect`)

## Open questions that are yours to chase

- [ ] What are the Linq track's prize and judging rules, and how many teams are on it?
- [ ] How fast can we get a Linq API key and a phone number at the event?
- [ ] Do we have enough iPhones (team plus demo volunteers) for blue-bubble group threads, or do the RCS and SMS fallbacks cover it?

## Definition of done for this part

Two people can text Plus One through Linq (one private thread each, plus a
group thread), messages land in the event log correctly tagged public/private,
and a whisper comes back to the right private thread — even with Brain still
stubbed. That's build-order step 1 in `SPEC.md`.
