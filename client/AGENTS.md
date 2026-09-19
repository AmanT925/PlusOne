# Expo HAS CHANGED

Read the exact versioned docs at https://docs.expo.dev/versions/v57.0.0/ before writing any code.

## Stream C: Voice and client

Owns: phone app, whisper button, speech to text, text to speech, earbud playback,
text fallback, counter screen, demo video.

Scope: only edit files under `/client`. Do not edit `/contracts/*` — those are
frozen; propose changes to the other stream owners instead.

Talks to the server only via the websocket message shapes documented in
`contracts/README.md` (`{type: "utterance", ...}` out, `{type: "whisper" | "public"
| "counter", ...}` in).

Work alone by pointing at a fake server that replies with canned whispers before
the real server (`/server`) is ready.
