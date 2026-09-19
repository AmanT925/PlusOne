# Handoff

Current state: repo scaffolded (see `README.md`), contracts frozen, each stream
has a stub. Nothing beyond the stubs is implemented yet. This file tracks what's
left, grouped by stream. See `SPEC.md` for the full context behind each item.

Plus One now runs on two channels over one brain: **iMessage via Linq** (the
everyday, no-install channel — private thread per person + one group thread)
and **earbud audio via the Expo app** (the in-person channel, plus a text
fallback if Linq access is slow). Both feed the same event log and the same
`context_for(viewer)` privacy boundary.

## Open questions (verify before/while building — SPEC.md "To verify early")

- [ ] What are the Linq track's prize and judging rules, and how many teams are on it?
- [ ] How fast can we get a Linq API key and a phone number at the event?
- [ ] Do we have enough iPhones (team plus demo volunteers) for blue-bubble group threads, or do the RCS and SMS fallbacks cover it?
- [ ] Do Muse Voice Transcribe and Grok Voice support streaming, and how do they handle several simultaneous sessions?
- [ ] Is a space theme required for the SpaceXAI challenge, or only Cursor plus a Grok API?
- [ ] Does Meta's Official Rules text limit submitting one project to several sponsors?
- [ ] What is the submission deadline?
- [ ] Has someone already shipped a shared, privacy-aware multi-person agent? (10 min search)
- [ ] Is the "Plus One" name and a matching domain/repo name free?
- [ ] First-hour latency check: measure end-of-speech-to-start-of-whisper time. Target <3s. If much slower, stay on iMessage only and decide early.

## Stream A: Core (`/server`)

- [ ] **Linq adapter** — receive inbound webhooks (private thread -> `visibility: private:<user>` event, group thread -> public event) and send outbound messages (whisper -> one-on-one thread, public suggestion -> group thread). See `contracts/README.md` "Linq mapping".
- [ ] Get a Linq API key and phone number, confirm webhook delivery end to end
- [ ] Multi-room support (`main.py` currently assumes one global room/event log)
- [ ] Wire real `brain.py` functions in place of `stub_write_whisper`
- [ ] Persist event log to SQLite for replay (currently in-memory only, per SPEC.md "Stack")
- [ ] `context_for(viewer)` — the actual privacy-boundary function described in SPEC.md; `main.py` doesn't build per-viewer context yet, it only stubs the whisper text
- [ ] HTTPS tunnel for phones/Linq webhooks to reach the server during dev and demo
- [ ] Reconnect handling / graceful handling of dropped websockets beyond the current bare `except WebSocketDisconnect`

## Stream B: Brain (`/brain`)

All four functions in `brain.py` currently raise `NotImplementedError`:

- [ ] `extract_constraints(event)` — parse a private utterance into `Constraint` objects (budget_cap, date_block, avoid_person, energy; hard/soft)
- [ ] `group_summary(constraints)` — produce the anonymous group summary string (e.g. "budget ceiling is about $150") that whispers and public speech are allowed to see
- [ ] `write_whisper(viewer_context)` — one- or two-sentence whisper per person from a `ViewerContext`
- [ ] `should_whisper(state)` — timing rules: only when the public proposal conflicts with a private constraint, the person isn't mid-sentence, and ~20s have passed since their last whisper
- [ ] Plan scoring — score candidate plans against everyone's constraints (not yet represented anywhere in the code)
- [ ] Inference-leak mitigation — keep plans varied so a price change can't be traced back to one speaker
- [ ] Leak-test harness — scripted extraction attempts **through both the private threads and the group thread**, logs attempts-vs-leaks count (good Devin candidate per SPEC.md)
- [ ] Token logging — log token counts per run, with and without compression, for The Token Company's before/after number
- [ ] Context compression / routing cheap steps to a small model (Token Company requirement)
- [ ] Fixture groups in `/fixtures` to test all of the above without a server

## Stream C: Voice and client (`/client`)

Expo app is scaffolded (default template `App.tsx`) but has none of the product UI yet. Scope has narrowed: the everyday texting flow now lives in iMessage via Linq (stream A owns that), so this app is for the in-person audio experience plus a fallback screen:

- [ ] Earbud audio experience: speech-to-text input, text-to-speech + earbud playback for whispers
- [ ] Speech-to-text integration (Muse Voice Transcribe)
- [ ] Text-to-speech integration (Grok Voice)
- [ ] Bare text fallback screen — used if Linq access is slow at the event; shown as text on the phone if audio is flaky
- [ ] Counter screen showing shared/total constraint count (good Devin candidate per SPEC.md)
- [ ] Websocket client connecting to the server using the `contracts/README.md` message shapes, for the audio/fallback path
- [ ] Fake-server mode with canned whispers from `/fixtures`, for working without stream A
- [ ] Demo video recording

## Cross-stream / integration (SPEC.md "Integration points")

- [ ] Text loop working end to end: two people texting through Linq (private thread each, one group thread) get whispers back (needs A's Linq adapter + B)
- [ ] Voice plugged into the working text loop (Expo app: STT/TTS)
- [ ] Leak counter: B's harness running against A's real server (both threads), C displaying the result

## Submission checklist (SPEC.md)

- [ ] Working prototype
- [ ] 2-3 minute demo video
- [ ] Public code repository
- [ ] Short write-up: who it's for, how it strengthens connection, why AI is essential
- [ ] Token counts logged with and without compression
- [ ] Extraction-attempt results recorded (attempts versus leaks)

## Cut order if short on time (SPEC.md)

If behind schedule, cut in this order: **earbud audio** → whisper timing polish
→ Token Company compression → live audience extraction (keep the pre-run leak
number). **Never cut:** the privacy boundary or the iMessage loop.
