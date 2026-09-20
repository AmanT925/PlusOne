# Plus One

*The extra guest who keeps your secrets.*

Plus One is an AI that joins your group's plans and helps everyone say what they actually mean. Each person privately tells it their real limits (budget, dates, energy, people they'd rather avoid), by voice or text. Plus One weighs everyone's limits together, suggests a plan the whole group can say yes to, and whispers personal nudges to individuals along the way. It never reveals who said what.

Built for HackMIT 2026. Demo video: [add YouTube link]. Full team plan: [SPEC.md](SPEC.md).

## Who it's for

Friend groups, roommates, and families who avoid saying "I can't afford that" or "I don't want to go" in front of everyone. Those things go unsaid, so plans quietly fall apart: people go along and resent it, or drop out.

## How it brings people closer

Plans get made around what people can really do, not what they're willing to admit in a group chat. Nobody has to explain themselves, and nobody gets left out. The group just sees a plan that fits.

## Why AI is essential

Plus One only works if there's one participant everyone can be honest with. It takes in people's real limits in their own words, out loud or in text, weighs them against each other, and writes a personal nudge for each person and a plan line for the group. A group chat can't do that because everyone can see it, and a form can't because nobody fills one out honestly in front of their friends.

## How privacy works

Privacy is a data filter, not a "please don't leak" prompt.

- Every message is an event tagged `public` or `private:<user>`. Linq DMs are private, and the group thread is public.
- Before any model call, `context_for(viewer)` builds the input from only the public log, that viewer's own private messages, and an anonymous `group_summary` (for example, "budget ceiling is about $150"). The model never sees anyone else's private text.
- Private messages are never broadcast. WebSocket replay is public-only, and whispers go only to that person's socket and their 1:1 Linq thread, never to the group.
- A leak harness (`brain/leak_test.py`) fails if another person's private text or name shows up in a summary or whisper. The server reports attempts versus leaks at `GET /rooms/{id}/leaks`, and on our fixture groups it reports zero leaks.

## Token results

On our sample room, this design used **68.7% fewer tokens** than sending the full event log to the model. Extraction, scoring, and the group summary are rule-based (zero tokens). Only whisper-writing calls an LLM, on the already-compressed context, capped at about 120 tokens out, with a zero-token template if the LLM is off. Reproduce it:

```bash
python -m brain.token_compare
```

Run it with the LLM on, or the comparison is meaningless.

## Built with

- **Meta Muse:** Muse Spark writes the whispers (Grok is the fallback), and Muse Voice Transcribe handles speech to text.
- **Grok:** Grok Voice plays whispers back, Grok Imagine draws a still from the public plan line, and we used Grok to plan the project.
- **Linq:** iMessage, with a private thread per person plus one group thread.
- **Cursor:** the whole project was built in Cursor, each of us running agents inside our own folder.

## Team

- **Aman:** the brain (constraint extraction, plan scoring, group summary, whisper writing, leak test, token comparison)
- **Nirvan:** the core (realtime server, event log, `context_for`, Linq integration)
- **Nikhil:** voice and client (web app, speech to text and text to speech, whisper playback, demo)

## Stack

- **Server** (`/server`, stream A: Core) — Python, FastAPI, websockets, plus a Linq adapter for iMessage/RCS/SMS webhooks
- **Brain** (`/brain`, stream B) — Python, plain functions, no server dependency
- **Client** (`/client`, stream C) — Expo (React Native): the web app with hold-to-talk voice, and the in-person earbud-audio channel
- **Contracts** (`/contracts`) — frozen shapes shared by all three streams
- **Fixtures** (`/fixtures`) — sample groups and canned whispers for offline dev

Plus One runs on two channels over one brain: iMessage (via [Linq](https://linqapp.com/imessage-api)) is the everyday, no-install channel — a private thread per person plus one group thread — and earbud audio is the in-person channel. Both feed the same event log and the same `context_for(viewer)` privacy boundary. See `SPEC.md` for the full picture.

## Running the server

API keys for Muse, Grok, and Linq are read from `.env`. Without a key, whispers fall back to zero-token templates.

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
