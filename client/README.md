# Testing microphone input

Start the backend from the repository root (`python3 -m server`) and Expo from
this folder (`npm start`). Install backend dependencies with
`python3 -m pip install -r server/requirements.txt`; PyAV converts phone AAC
recordings to the mono PCM WAV required by Muse.

In Expo Go, disable Fake server and configure your computer's current LAN host
with port 8000. Tap sit down and wait for live.

1. Press and hold **Whisper** (private) or **Table** (public).
2. Allow microphone access on first use, then hold again and wait for Listening.
3. Speak while holding; release to upload and send. A pending “hearing you…”
   message is replaced by the Muse transcript.
4. Tap **play voice** on the reply to hear it.

Tap Whisper/Table briefly to send typed text. The server accepts clips under
90 seconds and uploads under 10 MiB. Keep test recordings short. Recording
requires a live connection; practice mode uses canned responses.

The server requires `MUSE_TRANSCRIBE_KEY`, `MUSE_API_KEY`, or `MODEL_API_KEY`;
`PLUSONE_STT=0` disables transcription. Keys remain on the server. Uploads are
multipart requests to `/rooms/{room}/audio`, never the transcript bypass.
The existing 20-second whisper cooldown still applies.

Manual checks: deny microphone permission (visible feedback), hold Whisper
(private transcript stays on the sender's phone), hold Table (both users see
the public transcript), and play a reply after recording. Browser recording
needs a secure context; use Expo Go for LAN phone testing.

References: [Expo Audio SDK 57](https://docs.expo.dev/versions/v57.0.0/sdk/audio/),
[Muse transcription](https://dev.meta.ai/docs/speech-to-text).
