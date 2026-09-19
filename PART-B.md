# Part B — Voice & sponsor APIs (`feat/voice-sponsors`)

Fork from `dev`. Owns **Grok Voice / Imagine in the running product** (SpaceXAI requires one of these; Grok Bot is bonus only) and any Linq media (voice memo) needed for that.

**Do not** edit `/contracts`. **Do not** rewrite Brain prompts (that is `feat/intelligence`). **Do not** restyle the Expo screens (that is `feat/client-ux`) except a minimal “play whisper audio” control if the UI branch has not landed.

## You own

1. **Grok Voice** — TTS of whisper text with `XAI_API_KEY` (`POST https://api.x.ai/v1/tts` or realtime). Prefer server-side so keys stay out of the app. Deliver via Expo playback **or** Linq voice memo to the 1:1 thread.
2. **Grok Imagine fallback** — if Voice is blocked, generate one still of the agreed trip and send it to the **group** thread so the project still uses Imagine.
3. **Latency** — aim &lt;3s from whisper text ready to audio start. If slower, keep iMessage text and still call Voice/Imagine once in the demo.
4. **Optional** — Muse Voice Transcribe for hold-to-talk once Meta credits work; not a substitute for Grok Voice/Imagine.

## Done when

- [x] Server-side Grok Voice TTS (`server/xai.py`) with `XAI_API_KEY`
- [x] Whisper path: text always; Linq voice memo when TTS works; optional `audio_url` for Expo Play
- [x] Grok Imagine fallback to the group thread if Voice fails
- [x] `/demo/sponsors/voice` and `/demo/sponsors/imagine` for screenshot + working call
- [x] `.env.example` documents `XAI_API_KEY` / `PLUSONE_PUBLIC_BASE_URL`

A demo path clearly uses Voice **or** Imagine (screenshot + working call). Text whispers still work if audio fails.

## Files

`/server` TTS/Imagine helpers, `/client` playback only as needed, `.env.example` for `XAI_API_KEY`.
