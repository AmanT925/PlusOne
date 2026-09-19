#!/usr/bin/env python3
"""Software stand-in for a Korvo: websocket client + optional audio POST.

Usage (repo root):
  python hardware/korvo/sim_client.py --host localhost:8000 --user sam --room demo
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

try:
    import websockets
except ImportError:
    print("pip install websockets httpx", file=sys.stderr)
    raise


ROOT = Path(__file__).resolve().parents[2]


def ws_url(host: str, room: str, user: str) -> str:
    host = host.removeprefix("http://").removeprefix("https://").removeprefix("ws://").removeprefix("wss://")
    return f"ws://{host}/ws/{room}/{user}"


async def receiver(ws) -> None:
    async for raw in ws:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            print("<<", raw)
            continue
        kind = msg.get("type")
        if kind == "whisper":
            audio = msg.get("audio_url")
            print(f"\n<< WHISPER: {msg.get('text')}")
            if audio:
                print(f"   audio_url: {audio}")
        elif kind == "public":
            print(f"\n<< PUBLIC [{msg.get('speaker')}]: {msg.get('text')}")
        elif kind == "counter":
            print(f"\n<< COUNTER {msg.get('shared')}/{msg.get('total')}")
        else:
            print("\n<<", msg)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Korvo simulator for Plus One")
    parser.add_argument("--host", default="localhost:8000")
    parser.add_argument("--room", default="demo")
    parser.add_argument("--user", default="sam")
    parser.add_argument(
        "--via-audio",
        action="store_true",
        help="Send private lines via POST /audio with transcript bypass (no Muse)",
    )
    args = parser.parse_args()

    url = ws_url(args.host, args.room, args.user)
    print(f"Connecting {url}")
    print("Enter = private whisper text | p <text> = public | q = quit")

    async with websockets.connect(url) as ws:
        recv_task = asyncio.create_task(receiver(ws))
        loop = asyncio.get_event_loop()
        try:
            while True:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                line = line.rstrip("\n")
                if line.lower() in ("q", "quit", "exit"):
                    break
                if line.lower().startswith("p "):
                    text = line[2:].strip() or "let's do the fancy resort"
                    visibility = "public"
                else:
                    text = line.strip() or "I can't do more than 150 this month"
                    visibility = f"private:{args.user}"

                if args.via_audio and visibility.startswith("private:"):
                    # Tiny silent WAV so multipart is valid; transcript bypasses Muse.
                    wav = _silent_wav()
                    http_host = args.host if "://" in args.host else f"http://{args.host}"
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            f"{http_host}/rooms/{args.room}/audio",
                            data={
                                "speaker": args.user,
                                "visibility": visibility,
                                "transcript": text,
                            },
                            files={"audio": ("u.wav", wav, "audio/wav")},
                        )
                    print(f">> AUDIO {response.status_code} {response.text[:200]}")
                else:
                    await ws.send(
                        json.dumps(
                            {"type": "utterance", "visibility": visibility, "text": text}
                        )
                    )
                    print(f">> {visibility}: {text}")
        finally:
            recv_task.cancel()


def _silent_wav(ms: int = 100, rate: int = 16000) -> bytes:
    sys.path.insert(0, str(ROOT))
    from server.wavutil import pcm16_to_wav

    n = int(rate * ms / 1000)
    return pcm16_to_wav(b"\x00\x00" * n, sample_rate=rate)


if __name__ == "__main__":
    asyncio.run(main())
