# Plus One — technical plan (`dev`)

HackMIT 2026 (Sep 19–20). All remaining work happens on branch `dev`.
`/contracts` stays frozen unless all stream owners agree.

**Get keys / accounts:** follow [HACKMIT-SETUP.md](HACKMIT-SETUP.md). **Remaining work from the live iMessage whisper:** [NEXT.md](NEXT.md).

Plus One line (Linq): **+1 (949) 278-3794** → E.164 `+19492783794`.

---

## Product in one paragraph

A group plans in public (talking, group iMessage, or **Table** in the app). Each person also has a private channel (1:1 iMessage or **Whisper** / earbud). They tell the agent real constraints (budget, dates, people to avoid). The agent whispers a nudge **only to that person** and may post **one** table-safe suggestion. It never quotes a private message or names who needed what. The originality claim is `context_for(viewer)` in code, not a prompt.

Pitch: *plan the trip everyone can actually afford, without anyone having to say it.*

---

## Current baseline

Already on `dev`:

- SQLite event log, multi-room, websocket reconnect + public replay
- `context_for(viewer)` privacy boundary
- Heuristic Brain (`extract_constraints`, `group_summary`, `write_whisper`, `should_whisper`, `score_plan`)
- Fixture leak harness (0 leaks / 5 attempts)
- Linq live loop: 1:1 inbound → private event → whisper back on iMessage (`python -m server.dev`)
- Expo text UI (Fake server / live WS, Whisper vs Table, `shared/total`)

Not done: LLM whispers (still a template), public plan suggestion in the live loop, leak number on a screen, earbud STT/TTS, token before/after, demo video / write-up.

---

## Invariant

No model ever sees another person’s private events. Only:

| Output | Allowed inputs |
|---|---|
| Whisper to U | `context_for(U)`: public log, U’s private events, anonymous `group_summary` |
| Public suggestion | public log + the same anonymous summary |

Regex extractors may read a **single** private event (already that speaker’s).

---

## Phase 0 — Demo script = acceptance test

~2–3 minutes:

1. Group drifts toward an expensive option (public / group thread).
2. Two people privately send a budget cap and an avoid-person constraint.
3. Each gets a **different** whisper; the table gets **one** public suggestion; counter moves; no private numbers/names appear in public.
4. Someone tries to extract a secret through the group channel; attempts go up, leaks stay 0.

Cut anything that does not serve this script.

---

## Phase 1 — Linq live loop

**Goal:** text `+19492783794`. 1:1 inbound → `private:<user>`; group inbound → `public`; whisper → that 1:1; public suggestion → group thread.

Code already in `server/linq.py`, `POST /linq/webhook`. Remaining:

1. HTTPS tunnel (ngrok — see below).
2. Webhook subscription with `message.received` and `?version=2026-02-03`.
3. Store `LINQ_WEBHOOK_SECRET` (`whsec_...`) in gitignored `.env`.
4. `LINQ_FROM=+19492783794` so outbound uses this line.
5. Optional `GET /v3/phone_numbers` on boot; log count only (never log the API key).

**Acceptance:** Sam DMs a budget; Priya DMs an avoid; group says “$400 resort”; only Sam’s 1:1 gets Sam’s whisper; group thread never quotes the budget.

### What is a webhook secret?

Linq does not “call your laptop” until you **subscribe**. You give them an HTTPS URL. They POST every inbound iMessage to that URL, and they **sign** the body with HMAC.

The **signing secret** (`whsec_...`) is a password Linq shows **once** when the subscription is created. Our server uses it to prove the POST really came from Linq (`server/linq.py` `verify_signature`). It is **not** the API key. Without it (or `LINQ_SKIP_VERIFY=1` for local unsigned tests only), inbound iMessage is rejected.

### Where to create the subscription

There usually is **no required dashboard click**. Create it with the Partner API (Linq sandbox / API key you already have):

```bash
curl https://api.linqapp.com/api/partner/v3/webhook-subscriptions \
  -H "Authorization: Bearer $LINQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"target_url\":\"https://YOUR_NGROK/linq/webhook?version=2026-02-03\",\"subscribed_events\":[\"message.received\"]}"
```

Docs: [Create webhook subscription](https://docs.linqapp.com/api/resources/webhook_subscriptions/methods/create/).

Copy `signing_secret` from the JSON into `.env` as `LINQ_WEBHOOK_SECRET`. If you lose it, delete the subscription and create another.

If the Linq sandbox UI has a Webhooks page, same fields: URL, events = `message.received`, version `2026-02-03`.

### Tunnel: ngrok

Linq `target_url` **must be HTTPS**.

```bash
ngrok http 8000
```

Leave uvicorn on `:8000`. Put the printed `https://….ngrok-free.app` into the subscription URL (path `/linq/webhook?version=2026-02-03`).

Ngrok URLs change each process unless you have a reserved domain — recreate the webhook subscription when the URL changes, or set `LINQ_SKIP_VERIFY=1` only for throwaway local tests (not for the demo).

---

## Phase 2 — Brain that feels like a product

Keep regex as the offline/fast path. LLM only on `ViewerContext` / already-anonymous summary.

| Function | Now | Target |
|---|---|---|
| `extract_constraints` | regex | regex first; if empty, small/cheap model on **that private event only** |
| `group_summary` | deterministic anonymous string | keep; optional paraphrase of that string only |
| `write_whisper` | template | LLM, 1–2 sentences |
| `should_whisper` | 20s + conflict | stay in code |
| `score_plan` / `pick_plan` | unused | Core calls after public conflict → `maybe_public_suggestion` |

**Public suggestion:** 3–5 canned candidate plans (cheap picnic, mid restaurant, fancy resort). `pick_plan` prefers a fit that is not uniquely explained by one person’s hard cap.

**Leak harness:** scripted extraction through **group and private** against the real server; persist `{attempts, leaks}`.

**Tokens:** `brain/tokens.py` around every LLM call; one fixture run regex-only vs LLM for Token Company.

**Acceptance:** weekend_trip fixture → Sam’s whisper never contains Priya’s secret or “Alex” unless it was already public.

---

## Phase 3 — Client: leak display, then audio

Frozen WS: `utterance` out; `whisper` / `public` / `counter` in.

- **Leak screen:** `GET /rooms/{id}/leaks` on a laptop “table display” (avoids unfreezing WS).
- **Voice:** hold-to-talk → server-side STT → same `utterance`; `{type:whisper}` → TTS on that phone. Measure **&lt;3s** end-of-speech to audio start. If slower, keep text + iMessage.
- Mic/TTS likely needs an Expo **dev client**, not Expo Go.
- Keys stay on the server, not in the app.

---

## Phase 4 — Demo package

- Quote pre-run leak number (“N attempts, 0 leaks”).
- 2–3 min video matching the script.
- Write-up: who it’s for, connection, why AI is essential (`context_for`).
- Public repo; `.env` gitignored.
- Token table with vs without compression.

---

## Sequencing and cuts

```
Linq E2E → LLM whispers + public suggestion → leak number on a screen
  → (optional) voice if <3s → video / write-up
```

**Never cut:** `context_for`, iMessage/text loop.  
**Cut first:** earbuds → timing polish → token compression → live judge attack (keep the pre-run number).

All of this is implemented on **`dev`** (no split back to part branches unless we need parallel PRs later).

---

## File map

| Area | Files |
|---|---|
| Core | `server/linq.py`, `rooms.py`, `main.py`, webhook bootstrap, ngrok notes |
| Brain | `brain/brain.py`, `tokens.py`, `leak_test.py`, `/fixtures` |
| Client | leak display, later audio; keep text fallback |
| Contracts | do not edit |

---

## Phones and “names”

Two different phone concepts:

1. **Plus One’s Linq line** — `+19492783794`. People text **this**. We have it.
2. **Humans’ phones** — Sam’s and Priya’s personal numbers. Those appear on inbound webhooks as `sender_handle`.

In the Expo app you type a **name** (`sam`, `priya`). In iMessage, Linq only sees `+1555…`. `PLUSONE_HANDLES` glues them so one person is one `speaker` in the event log:

```text
PLUSONE_HANDLES=sam:+15551111111,priya:+15552222222
```

Without the map, Linq users are stored as their E.164 string. That still works for an iMessage-only demo. You need the map only if the **same human** uses Expo **and** iMessage and should share one private log.

**What to send when you have it:** for each volunteer, a display name + their number in E.164 (`+1` and digits, no spaces). Example: `nirvan:+16175551212`. Not required to start Linq; required to merge app + iMessage identity.

---

## Grok Bot vs Muse vs what the product needs

**Grok Bot (Cursor / SpaceXAI “create a bot”) is not enough for runtime whispers.**

| Thing | What it is | Enough for Plus One? |
|---|---|---|
| **Grok Bot** | Persistent coding/agent teammate in Cursor’s cloud. You message it to write code, browse, run terminals. | Good for **building** (and likely the SpaceXAI “use Grok Bot / Cursor” checkbox). It does **not** sit on our FastAPI box answering each iMessage in &lt;3s. |
| **Grok / xAI API** (chat completions) | HTTP API: send `ViewerContext`, get 1–2 sentences. | **This** is what `write_whisper` needs. |
| **Grok Voice API** | TTS / realtime audio. | Earbuds only (Phase 3). |
| **Muse Spark / Muse Voice Transcribe** | Meta hackathon stack. | Spark can replace/supplement Grok for whispers; Transcribe is STT. You said Muse access is incoming — plug it in when you have the key. |

Practical split for HackMIT:

- Create the Grok Bot if the sponsor doc requires it; use it as a teammate while we code on `dev`.
- For the **demo product**, we still need an **API key** (xAI `XAI_API_KEY` / Grok, and/or Muse when you get it). Put it in `.env`. Never ship it in Expo.

If the Google doc only says “make a Grok Bot” and never mentions the developer API, ask a SpaceXAI mentor whether Bot-only counts. Until then: Bot for the prize checkbox, API for whispers.

The sponsor doc (`https://docs.google.com/document/d/1JxZA0eiX2iWj_-B5xtCo59FylUDlv3I35n5n8W0aIVs/edit`) was not readable from here (export timed out). Paste the Grok / Muse / Linq sections into chat if you want the plan matched to exact judging rules.

---

## Env template (repo-root `.env`, gitignored)

```text
LINQ=                        # already set
LINQ_FROM=+19492783794
LINQ_WEBHOOK_SECRET=whsec_...
PLUSONE_ROOM_ID=demo
# PLUSONE_HANDLES=sam:+1...,priya:+1...
# XAI_API_KEY=                 # Grok chat for write_whisper
# MUSE_API_KEY=                # when you get it
```

---

## Next concrete steps on `dev`

1. Document ngrok + webhook curl in `server/README.md` (this file is the plan; README stays the runbook).
2. Add `LINQ_FROM` support and a small `python -m server.subscribe_linq` helper that creates the webhook once ngrok is up.
3. LLM `write_whisper` behind `XAI_API_KEY` / Muse, regex fallback if missing.
4. Wire `pick_plan` → public suggestion on conflicting public utterances.
5. iMessage E2E once tunnel + `LINQ_WEBHOOK_SECRET` exist.

---

## Still useful from you (non-blocking except where noted)

| Item | Need |
|---|---|
| Ngrok running + HTTPS URL | **Required** for inbound iMessage |
| `signing_secret` pasted into `.env` | **Required** for verified webhooks (or we create the subscription for you once the tunnel URL exists) |
| Volunteer E.164 + names | Optional until app+iMessage merge |
| xAI / Grok **API** key (not only Bot) | Required for LLM whispers |
| Muse key | When you have it; we keep regex/Grok until then |
| Paste of sponsor doc Grok/Muse/Linq rules | So we don’t miss a judging checkbox |
