# Product close-out (temp UI) — then merge real UX later

Stay on `dev`. **Do not** edit `/contracts`. **Do not** commit `.env`. The revamp in `feat/client-ux` stays out until that stream is done; this plan ships a **temporary Expo UI** so Voice + Imagine + Brain + Linq can be demoed now.

## Already on `dev`

- Private DMs → whispers (`context_for`); Muse then Grok then template
- Group plans (Switzerland, `$400` resort) → anonymous cheaper suggestion in the **group**
- Leak API `GET /rooms/{id}/leaks`
- Token log / `python -m brain.token_compare`
- Imagine still attempted on the **first** group suggestion (Linq link)
- Existing Expo text fallback (debug form, fake-server default)

## Build now

### 1. Grok Voice (TTS)

- `server/xai_media.py`: `speak_whisper(text) -> bytes | None` via `POST https://api.x.ai/v1/tts` (`voice_id=eve`, `language=en`), same `XAI_API_KEY`.
- After a whisper is written, synthesize **then** deliver text so the mp3 is ready.
- `GET /rooms/{room}/users/{user}/whisper.mp3` — last audio for that viewer only (hackathon demo; no auth).
- Flag `PLUSONE_TTS=0` in tests. Text still works if Voice is denied.

### 2. Imagine (Expo + Linq)

- Keep Linq group link send.
- Persist last still URL on the hub: `GET /rooms/{room}/media` → `{imagine_url}`.
- Temp app shows the still when present.

### 3. Temporary Expo UI (`/client`)

- Table vs Whisper as primary actions; setup (name / room / host / fake) in a collapsed sheet.
- Hero `shared/total` + leak `attempts/leaks` from HTTP.
- Live WebSocket default; fake-server is opt-in.
- Play control on a whisper (HTTP mp3). Frozen WS shape stays `{type: whisper, text}`.
- Same `demo` room as iMessage.

### 4. Out of scope until `feat/client-ux`

Final visual system, hold-to-talk polish, earbud pairing chrome. Merge that branch later.

## Demo after this lands

1. `python -m server.dev`
2. Expo Go (or `--web`): live host `LAN:8000`, name matching `PLUSONE_HANDLES`
3. Whisper `$150` in-app → text + Play
4. Table `going to Switzerland` → group-style public line + optional still
5. iMessage group still works on the same room

## Expo Go vs native build

**No dev build.** Playback uses `expo-audio`, which Expo Go for SDK 57 already includes. Do **not** add the `expo-audio` config plugin (background/mic) — that would force a rebuild.

Everyone: install **Expo Go**, same Wi‑Fi as the laptop, scan the QR from `npx expo start`. That loads the UI. Each person must set **their name** and the laptop **LAN IP:8000** (not `localhost`). The QR does not tunnel the Python API.
