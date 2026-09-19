"""Speech-to-text for Korvo / hold-to-talk audio.

Primary: Meta Muse Voice Transcribe (PUSH_TO_TALK WAV upload).
Dev bypass: pass `transcript` alongside audio (no Muse call).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

log = logging.getLogger("plusone.stt")

MUSE_TRANSCRIBE_URL = "https://api.meta.ai/v1/asr/transcribe"
MUSE_MODEL = "muse-voice-transcribe-1.0"


def muse_api_key() -> str:
    return (
        os.environ.get("MUSE_TRANSCRIBE_KEY")
        or os.environ.get("MUSE_API_KEY")
        or os.environ.get("MODEL_API_KEY")
        or ""
    ).strip()


def stt_enabled() -> bool:
    return bool(muse_api_key())


async def transcribe_wav(wav_bytes: bytes, *, timeout: float = 30.0) -> str:
    """Upload mono 16-bit WAV → transcript text. Raises on failure."""
    key = muse_api_key()
    if not key:
        raise RuntimeError("MUSE_API_KEY / MUSE_TRANSCRIBE_KEY is not set")
    if not wav_bytes:
        raise ValueError("empty audio")

    request_json = {
        "model": MUSE_MODEL,
        "audioEncoding": "WAV",
        "mode": "PUSH_TO_TALK",
    }
    files = {
        "request": (None, json.dumps(request_json), "application/json"),
        "audio": ("utterance.wav", wav_bytes, "audio/wav"),
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(MUSE_TRANSCRIBE_URL, headers=headers, files=files)
    if response.status_code >= 400:
        raise RuntimeError(f"Muse STT {response.status_code}: {response.text[:400]}")
    data = response.json()
    text = _extract_transcript(data)
    if not text:
        raise RuntimeError(f"Muse STT returned no transcript: {str(data)[:300]}")
    log.info("Muse STT ok chars=%s", len(text))
    return text


def _extract_transcript(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    direct = data.get("transcript")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    turns = data.get("turns")
    if isinstance(turns, list):
        chunks: list[str] = []
        for turn in turns:
            if isinstance(turn, dict) and turn.get("transcript"):
                chunks.append(str(turn["transcript"]).strip())
        return " ".join(c for c in chunks if c).strip()
    return ""
