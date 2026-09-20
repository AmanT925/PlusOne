"""Optional LLM whispers. Muse first, Grok fallback. Never send others' private events."""

from __future__ import annotations

import logging
import os
import re

from contracts.schema import ViewerContext

log = logging.getLogger("plusone.llm")

_MUSE_URL = os.environ.get("MUSE_BASE_URL", "https://api.meta.ai/v1/chat/completions")
_MUSE_MODEL = os.environ.get("MUSE_MODEL", "muse-spark-1.1")
_GROK_URL = "https://api.x.ai/v1/chat/completions"
_GROK_MODEL = os.environ.get("XAI_MODEL", "grok-3")


def llm_enabled() -> bool:
    flag = os.getenv("PLUSONE_LLM", "1").lower()
    if flag in ("0", "false", "no", "off"):
        return False
    return bool(os.getenv("MUSE_API_KEY") or os.getenv("XAI_API_KEY"))


def _sentence_cap(text: str, limit: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = [p.strip() for p in parts if p.strip()][:limit]
    out = " ".join(kept).strip()
    if out and out[-1] not in ".!?":
        out += "."
    return out


def _other_names(ctx: ViewerContext) -> set[str]:
    viewer = ""
    if ctx.own_private_events:
        viewer = ctx.own_private_events[-1].speaker.lower()
    names = {event.speaker.lower() for event in ctx.public_log}
    names.discard(viewer)
    names.discard("plus-one")
    names.discard("plusone")
    return {n for n in names if n}


def _leaks(text: str, others: set[str]) -> bool:
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(name)}\b", lowered) for name in others)


def _prompt(ctx: ViewerContext) -> str:
    public = "\n".join(
        f"- {event.text}" for event in ctx.public_log[-8:]
    ) or "(none yet)"
    own = "\n".join(
        f"- {event.text}" for event in ctx.own_private_events[-6:]
    ) or "(none yet)"
    return (
        "Write a 1-2 sentence private whisper to this one person.\n"
        "You may use: the public table talk, THEIR private notes, and the anonymous group summary.\n"
        "Never name other people. Never quote someone else's private message. "
        "Never say who needed what. If the public plan fights their limits, nudge a fitting alternative.\n\n"
        f"Anonymous group summary:\n{ctx.group_summary}\n\n"
        f"Public table talk:\n{public}\n\n"
        f"This person's private notes:\n{own}\n"
    )


def _chat(url: str, token: str, model: str, prompt: str) -> str | None:
    try:
        import httpx
    except ImportError:
        return None
    try:
        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0.4,
                "max_tokens": 80,
                "messages": [
                    {
                        "role": "system",
                        "content": "You write short private nudges for Plus One. Two sentences max.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=8.0,
        )
        if response.status_code >= 400:
            log.warning("llm %s status %s", model, response.status_code)
            return None
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        return str(text).strip() or None
    except Exception:
        log.warning("llm %s failed", model, exc_info=True)
        return None


def llm_whisper(ctx: ViewerContext) -> str | None:
    if not llm_enabled():
        return None
    prompt = _prompt(ctx)
    others = _other_names(ctx)
    muse = os.getenv("MUSE_API_KEY", "").strip()
    grok = os.getenv("XAI_API_KEY", "").strip()
    text = None
    route = None
    if muse:
        text = _chat(_MUSE_URL, muse, _MUSE_MODEL, prompt)
        route = "muse"
    if not text and grok:
        text = _chat(_GROK_URL, grok, _GROK_MODEL, prompt)
        route = "grok"
    if not text:
        return None
    text = _sentence_cap(text, 2)
    if _leaks(text, others):
        log.warning("llm %s named someone; dropping", route)
        return None
    return text
