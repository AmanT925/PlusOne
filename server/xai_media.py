"""Grok Imagine (and later Voice) using XAI_API_KEY from .env. Never log the key."""

from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger("plusone.xai")


def _key() -> str:
    return os.environ.get("XAI_API_KEY", "").strip()


async def imagine_still(prompt: str) -> str | None:
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
