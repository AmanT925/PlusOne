# Testing microphone input

Start the backend from the repository root (`python3 -m server`) and Expo from
this folder (`npm start`). Install backend dependencies with
`python3 -m pip install -r server/requirements.txt`; PyAV converts phone AAC
recordings to the mono PCM WAV required by Muse.

In Expo Go, disable Fake server and configure your computer's current LAN host
with port 8000. Tap Hide setup and wait for Live.

1. Tap **Record whisper** (private) or **Record table** (public).
2. Allow microphone access, then speak after the recording timer appears.
3. Tap **Stop & send**. The app uploads the clip and displays the transcript in
   the conversation. Private replies arrive on the same user's socket.
4. Tap **Play voice** on the reply to hear it.

**Cancel** discards the recording without uploading. Leaving the foreground
cancels active recording. Clips automatically stop and send after 60 seconds.
Changing the room, user, or host discards an active recording. Recording is
disabled in fake mode and while disconnected. Typed Whisper/Table still work.

The server requires `MUSE_TRANSCRIBE_KEY`, `MUSE_API_KEY`, or `MODEL_API_KEY`;
`PLUSONE_STT=0` disables transcription. Keys remain on the server. Uploads are
multipart requests to `/rooms/{room}/audio`, never the transcript bypass.
The existing 20-second whisper cooldown still applies.

Manual checks: deny microphone permission (visible error), cancel (no message),
record privately (no private transcript on a second user's phone), record to the
table (both users see it), change identity mid-recording (discard), and play a
reply after recording (normal playback restored). Browser recording needs a
secure browser context; use Expo Go for LAN phone testing.

References: [Expo Audio SDK 57](https://docs.expo.dev/versions/v57.0.0/sdk/audio/),
[Muse transcription](https://dev.meta.ai/docs/speech-to-text).
