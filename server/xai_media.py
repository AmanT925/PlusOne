"""Grok Imagine (and later Voice) using XAI_API_KEY from .env. Never log the key."""

from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger("plusone.xai")


def _key() -> str:
    return os.environ.get("XAI_API_KEY", "").strip()


def _flag(name: str, default: str = "1") -> bool:
    return os.environ.get(name, default).strip().lower() not in ("0", "false", "no", "off")


def imagine_enabled() -> bool:
    return _flag("PLUSONE_IMAGINE") and bool(_key())


def tts_enabled() -> bool:
    return _flag("PLUSONE_TTS") and bool(_key())


async def speak_whisper(text: str) -> bytes | None:
    """Grok TTS. Returns mp3 bytes. Never logs the API key."""
    if not tts_enabled() or not (text or "").strip():
        return None
    key = _key()
    voice = os.environ.get("XAI_TTS_VOICE", "eve")
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(
                "https://api.x.ai/v1/tts",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={"text": text.strip()[:1500], "voice_id": voice, "language": "en"},
            )
        if response.status_code >= 400:
            log.warning("tts failed %s %s", response.status_code, response.text[:300])
            return None
        body = response.content
        if body and len(body) > 40:
            return body
        return None
    except httpx.HTTPError:
        log.exception("tts request failed")
        return None


async def imagine_still(prompt: str) -> str | None:
    if not imagine_enabled():
        return None
    key = _key()
    if not key:
        return None
    model = os.environ.get("XAI_IMAGINE_MODEL", "grok-imagine-image-2.0")
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(
                "https://api.x.ai/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={"model": model, "prompt": prompt, "n": 1},
            )
        if response.status_code >= 400:
            log.warning("imagine failed %s %s", response.status_code, response.text[:300])
            return None
        data = response.json().get("data") or []
        if not data:
            return None
        url = data[0].get("url")
        return str(url) if url else None
    except httpx.HTTPError:
        log.exception("imagine request failed")
        return None
