# Plus One × ESP32-S3-Korvo-1

Each person gets a Korvo. It listens for them, tags speech public or private
(hold button = private), sends that to Plus One Core, and plays the whisper
**only on the 3.5 mm headphone jack** — never the table speaker.

## Architecture

```
Korvo  --Wi-Fi-->  Core (/ws + /rooms/.../audio)  -->  Brain + Grok Voice
Korvo  <--MP3---  GET /media/{token} (whisper audio_url)
```

Same privacy model as the phone: one device = one speaker. No shared table mic.

## Phases

| Phase | What | Status |
|---|---|---|
| 0 | Wi-Fi, LED, play canned MP3 on jack | firmware scaffold |
| 1 | WebSocket: send `utterance`, receive `whisper` text | firmware + `sim_client.py` |
| 2 | Fetch `audio_url`, play on headphones | firmware hooks |
| 3 | Hold-to-whisper WAV → `POST /rooms/{room}/audio` → Muse STT | server done; I2S capture TBD on board |

## Server API (already on `feat/voice-sponsors`)

```bash
# Text (same as Expo)
curl -X POST http://HOST/rooms/demo/utterances \
  -H 'content-type: application/json' \
  -d '{"speaker":"sam","visibility":"private:sam","text":"cap at 150"}'

# Audio from Korvo (WAV or PCM16). Dev: pass transcript to skip Muse.
curl -X POST http://HOST/rooms/demo/audio \
  -F speaker=sam \
  -F visibility=private:sam \
  -F transcript="I can't do more than 150" \
  -F audio=@utterance.wav
```

Websocket: `ws://HOST/ws/demo/sam` — same JSON as Expo.

Set `PLUSONE_PUBLIC_BASE_URL=https://…ngrok…` so `audio_url` is absolute for the board.

## Simulate without hardware

```bash
# terminal 1
uvicorn server.main:app --host 0.0.0.0 --port 8000

# terminal 2
python hardware/korvo/sim_client.py --host localhost:8000 --user sam --room demo
```

Hold Enter to send a private canned whisper; `p` + Enter for public.

## Flash real Korvo

1. Install [ESP-IDF 5.x](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/get-started/).
2. `cd hardware/korvo && idf.py set-target esp32s3`
3. `idf.py menuconfig` → Plus One: Wi-Fi SSID/pass, server host, room, user.
4. `idf.py -p PORT flash monitor`

Wire headphones into the **3.5 mm jack**. Do not use the speaker for private audio.

## Button map (firmware defaults)

| Control | Action |
|---|---|
| Function button 1 (hold) | Private capture / send |
| Function button 2 | Toggle public listen (Phase 3+) |
| RGB | idle / listening / private / playing |

## Do not

- One Korvo for the whole table
- Play whispers on the onboard speaker
- Put `XAI_API_KEY` / `MUSE_API_KEY` on the device
