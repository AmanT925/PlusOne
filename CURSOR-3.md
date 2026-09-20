# Cursor 3 — Voice close-out (`feat/cursor-3-voice`)

Paste this whole file into the unused Cursor. Work from **`feat/cursor-3-voice`**, which is branched from current **`origin/dev`** (the working two-phone Expo loop).

`/contracts` is frozen. **Do not edit** `contracts/schema.py` or `contracts/README.md`. **Do not restyle** `/client` (the UI Cursor owns `feat/client-ux` and will merge after this works). **Do not commit `.env`.**

You own **making Voice + Imagine actually demoable** so the UI branch can merge.

## Checkout

```bash
git fetch origin
git checkout feat/cursor-3-voice
git pull
```

If the branch is missing: `git checkout -b feat/cursor-3-voice origin/dev`.

## Already done on `dev` (do not redo)

- Two-phone text loop: Whisper → gold `whisper · only you`; Table → plus-one cheaper plan
- Privacy: other people’s private events stay off the wire
- Grok TTS after a whisper (`server/xai_media.py` `speak_whisper`) → `GET /rooms/{room}/users/{user}/whisper.mp3`
- Expo **Play voice** on gold bubbles (`client/src/playAudio.ts`) — do not rebuild the chat UI
- Imagine on the **first** public suggestion this process, hardcoded picnic prompt, URL at `GET /rooms/{room}/media`
- Windows `python -m server` (selector loop). Leak poll does **not** run the full LLM harness

## You implement

### 1. Speech-to-text (highest priority)

Port from **`feat/voice-sponsors`** (do not merge that whole branch — it conflicts with current `dev`):

- `server/stt.py` — Muse Voice Transcribe `POST https://api.meta.ai/v1/asr/transcribe`
- `server/wavutil.py` — PCM16 → WAV
- `POST /rooms/{room_id}/audio` — form: `speaker`, `visibility` (`public` or `private:<user>`), optional `transcript` bypass, file `audio` (WAV or PCM16). Transcribe → **same** `hub.ingest` as typed utterances.

Tests: `server/tests/test_audio_ingest.py` (port and fix against current rooms). `PLUSONE_LLM=0` in tests. Flag STT off if no Muse key.

Done when: `curl` (or a one-shot script) uploading a wav as `private:sam` produces a whisper in the event log. Expo UI can stay typed; the UI Cursor will wire hold-to-talk to this POST.

### 2. Grok TTS must actually play

- After `_deliver_whisper`, TTS already runs in a task. Confirm `XAI_API_KEY` + `PLUSONE_TTS=1` writes mp3 bytes.
- Log `tts failed <status>` clearly. If Voice is denied, text still works.
- Optional: Linq **voice memo** to the 1:1 thread when TTS bytes exist (Linq sponsor). Do not block ingest on it.

Done when: `GET /rooms/demo/users/nirvan/whisper.mp3` returns 200 after a private `$150` whisper, and Expo **Play voice** plays it.

### 3. Imagine still matches the public plan

Today the prompt is hardcoded picnic/dinner and **ignores** the suggestion (`_ = suggestion` in `rooms.py`). That is why Switzerland produced a random dinner photo.

Change the Imagine prompt to describe the **public plus-one suggestion text only** (cheap local hang / mid-range dinner / not Alps). Never put private events, names, or budgets-as-owned-by-a-person into the prompt. Keep one still per room process. Still send Linq `send_link` when a group chat exists.

Done when: Table `going to Switzerland` → cheaper plus-one **and** a still that looks like that cheaper plan, not a random picnic if the suggestion is dinner, etc.

### 4. Do not do

- `/client` restyle, new screens, or contract shape changes
- Merging `feat/client-ux`
- Merging all of `feat/voice-sponsors` (Korvo firmware is optional/cut)
- Rewriting Brain prompts (`write_whisper` / `suggest_public`) except tiny fixes if ingest breaks
- Committing secrets

## Done when

1. STT POST ingest works without Expo.
2. Play voice returns real audio after a whisper (or TTS is logged as denied and text still works).
3. First plus-one Imagine still reflects the **public** suggestion.
4. `python -m pytest server/tests brain/tests -q` passes.
5. PR or merge into `dev`. Then the UI Cursor merges `feat/client-ux`.

## Copy for the other human

Tell them: *Checkout `feat/cursor-3-voice`, open `CURSOR-3.md`, execute that plan. Server/brain only. Do not touch the Expo layout.*
