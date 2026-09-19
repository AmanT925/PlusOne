# Plus One Korvo firmware (ESP32-S3-Korvo-1)

See [HARDWARE.md](../../HARDWARE.md) for the product plan.

## Build

```bash
. $HOME/esp/esp-idf/export.sh   # or your IDF path
cd hardware/korvo
idf.py set-target esp32s3
idf.py menuconfig   # Wi-Fi + Plus One host/room/user
idf.py -p /dev/ttyUSB0 flash monitor
```

## What works in this scaffold

- Wi-Fi STA
- WebSocket to `/ws/{room}/{user}`
- Hold button → send private canned utterance (Phase 1)
- On `whisper` → log text + `audio_url` (Phase 2: play on 3.5 mm jack)

## Still TODO on device

- Remap whisper GPIO + WS2812 to Korvo BSP pins
- I2S capture (ES7210) on hold → WAV → `POST /rooms/.../audio`
- HTTP download + ES8311 playback to **headphone only**

Until those land, use `sim_client.py` on a laptop against the same server.
