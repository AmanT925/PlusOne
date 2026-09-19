# Expo HAS CHANGED

Read the exact versioned docs at https://docs.expo.dev/versions/v57.0.0/ before writing any code.

## Stream C: Voice and client

Owns: earbud audio (speech to text, text to speech, earbud playback), the audio
phone app screen, the counter screen, demo video, and a bare text screen as a
fallback if Linq access is slow on the day. The primary everyday channel
(private/group threads) now runs over iMessage via Linq, owned by stream A —
this app is for the in-person earbud-audio experience plus that fallback.

Scope: only edit files under `/client`. Do not edit `/contracts/*` — those are
frozen; propose changes to the other stream owners instead.

Talks to the server only via the websocket message shapes documented in
`contracts/README.md` (`{type: "utterance", ...}` out, `{type: "whisper" | "public"
| "counter", ...}` in).

Work alone by pointing at a fake server that replies with canned whispers before
the real server (`/server`) is ready.
