"""xAI Grok Voice (TTS) and Grok Imagine helpers for Part B (feat/voice-sponsors).

Keys stay on the server — never ship XAI_API_KEY in the Expo app.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

log = logging.getLogger("plusone.xai")

XAI_API = "https://api.x.ai/v1"
TTS_URL = f"{XAI_API}/tts"
IMAGINE_URL = f"{XAI_API}/images/generations"


def xai_api_key() -> str:
    return (os.environ.get("XAI_API_KEY") or "").strip()


def voice_enabled() -> bool:
    if os.environ.get("PLUSONE_VOICE", "1").lower() in ("0", "false", "no", "off"):
        return False
    return bool(xai_api_key())


def imagine_enabled() -> bool:
    if os.environ.get("PLUSONE_IMAGINE", "1").lower() in ("0", "false", "no", "off"):
        return False
    return bool(xai_api_key())


async def synthesize_speech(
    text: str,
    *,
    voice_id: str | None = None,
    language: str = "en",
    timeout: float | None = None,
) -> bytes:
    """POST /v1/tts → raw MP3 bytes. Raises on missing key or HTTP errors."""
    key = xai_api_key()
    if not key:
        raise RuntimeError("XAI_API_KEY is not set")
    trimmed = (text or "").strip()
    if not trimmed:
        raise ValueError("empty text")

    voice = voice_id or os.environ.get("XAI_TTS_VOICE", "eve")
    timeout = timeout if timeout is not None else float(os.environ.get("XAI_TTS_TIMEOUT", "8"))
    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            TTS_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "text": trimmed[:15000],
                "voice_id": voice,
                "language": language,
            },
        )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if response.status_code >= 400:
        raise RuntimeError(f"xAI TTS {response.status_code}: {response.text[:300]}")
    audio = response.content
    if not audio:
        raise RuntimeError("xAI TTS returned empty body")
    log.info("xAI TTS ok bytes=%s latency_ms=%s voice=%s", len(audio), elapsed_ms, voice)
    return audio


async def generate_image(
    prompt: str,
    *,
    model: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """POST /v1/images/generations → {url} or {b64_json}."""
    key = xai_api_key()
    if not key:
        raise RuntimeError("XAI_API_KEY is not set")
    trimmed = (prompt or "").strip()
    if not trimmed:
        raise ValueError("empty prompt")

    model = model or os.environ.get("XAI_IMAGINE_MODEL", "grok-imagine-image-quality")
    timeout = timeout if timeout is not None else float(os.environ.get("XAI_IMAGINE_TIMEOUT", "60"))
    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            IMAGINE_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "prompt": trimmed[:4000],
                "n": 1,
                "response_format": "url",
            },
        )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if response.status_code >= 400:
        raise RuntimeError(f"xAI Imagine {response.status_code}: {response.text[:300]}")
    data = response.json()
    items = data.get("data") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise RuntimeError(f"xAI Imagine unexpected response: {str(data)[:300]}")
    first = items[0] if isinstance(items[0], dict) else {}
    url = first.get("url")
    if not url:
        raise RuntimeError("xAI Imagine returned no url")
    log.info("xAI Imagine ok latency_ms=%s model=%s", elapsed_ms, model)
    return {"url": url, "model": model, "latency_ms": elapsed_ms}


def trip_still_prompt(public_proposal: str) -> str:
    base = (public_proposal or "").strip() or "a weekend trip with friends"
    return (
        "Photorealistic travel photo for a group weekend plan that stays affordable: "
        f"{base}. Warm natural light, inviting, no text, no logos, no people's faces close-up."
    )
