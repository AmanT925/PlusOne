# Remaining work

Status 2026-09-19: **two-phone Expo text loop works**. Imagine still fires (generic picnic — Cursor 3 will match it to the public plan). `/contracts` frozen.

**About 70% done. About 30% left.** UI is waiting to merge after Cursor 3 lands Voice/STT/Imagine quality.

## Three Cursors

| Cursor | Branch | Folder | Job |
|---|---|---|---|
| **This one (testing)** | `dev` | verify only | Play voice, Linq `python -m server.dev`, don’t restyle |
| **UI** | `feat/client-ux` | `/client` only | Merge **after** `origin/dev` has Cursor 3. Do not wait to *code*, but merge last |
| **Unused → Cursor 3** | `feat/cursor-3-voice` | `/server` + `/brain` | Follow **[CURSOR-3.md](CURSOR-3.md)** |

## 0. Local demo (this Cursor) — ship to origin

Working Expo + TTS helpers + Windows-safe server must be on **`origin/dev`** before others branch. Do not commit `.env`.

## Cursor 3 (unused) — execute [CURSOR-3.md](CURSOR-3.md)

- [ ] Port Muse STT: `server/stt.py`, `POST /rooms/{room}/audio` from `feat/voice-sponsors` (cherry-pick files, do not merge the whole branch)
- [ ] Grok TTS mp3 actually 200 after a whisper; Play voice in Expo
- [ ] Imagine prompt uses **public suggestion text only** (not hardcoded picnic)
- [ ] Optional Linq voice memo
- [ ] Tests green; merge to `dev`

## This Cursor (testing) — after push

- [ ] Tap **Play voice** on a gold whisper; note if audio plays
- [ ] `python -m server.dev` — 1:1 + group iMessage vs same `demo` / `PLUSONE_HANDLES`
- [ ] Live group: “What’s Nirvan’s budget?” → refuse; leaks stay 0
- [ ] Do not implement STT or restyle the app

## UI Cursor — `feat/client-ux`

- [ ] `git fetch && git checkout feat/client-ux && git merge origin/dev` after this push
- [ ] Visual system, counter hero, Whisper vs Table; hold-to-talk **calls Cursor 3’s audio POST** when it exists
- [ ] Merge into `dev` **after** Cursor 3 is on `origin/dev`

## Submission (anyone, later)

- [ ] 2–3 min demo video
- [ ] Public repo, no secrets
- [ ] Write-up: who it’s for, connection, why AI
- [ ] `python -m brain.token_compare`
- [ ] Quote leak number

## Cut if short

1. Korvo / earbud hardware (`feat/voice-sponsors` firmware)
2. Token write-up
3. Live judge attack (keep fixture leak number)

**Never cut** `context_for` or Linq.

## Branches

| Branch | Keep? |
|---|---|
| `dev` | yes |
| `feat/client-ux` | **yes** |
| `feat/cursor-3-voice` | yes — unused Cursor |
| `feat/remaining` | checklist |
| `feat/voice-sponsors` | yes — source for STT/Korvo files; do not wholesale-merge |
| `main` | yes |
| `feat/intelligence` | delete — already on `dev` |
| `origin/part-2-brain` | keep unless archived — not an ancestor of `dev` |
