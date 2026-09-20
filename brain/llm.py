"""Muse Spark then Grok chat; never pass more than a ViewerContext."""

from __future__ import annotations

import os
from typing import Any

import httpx

from brain.tokens import log_tokens
from contracts.schema import ViewerContext

SYSTEM = (
    "You write a private 1-2 sentence whisper for one person in a group planning chat. "
    "Use only the anonymous group summary, the latest public plan, and this person's own notes. "
    "Never name other people. Never invent who a constraint belongs to. "
    "Do not quote anyone else's private text. No preamble, no quotes around the whole reply."
)


def llm_enabled() -> bool:
    flag = os.environ.get("PLUSONE_LLM", "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    return bool(os.environ.get("MUSE_API_KEY") or os.environ.get("XAI_API_KEY"))


def complete_whisper(ctx: ViewerContext) -> str | None:
    if not llm_enabled():
        return None
    user = _user_payload(ctx)
    muse = os.environ.get("MUSE_API_KEY", "").strip()
    if muse:
        text = _openai_chat(
            route="muse",
            base="https://api.meta.ai/v1",
            key=muse,
            model=os.environ.get("MUSE_MODEL", "muse-spark-1.1"),
            user=user,
            # muse-spark-1.1 is a reasoning model: it spends completion tokens on
            # hidden reasoning before any visible text. Too low a cap (e.g. 120)
            # burns the whole budget on reasoning and returns content=null.
            max_tokens=500,
            extra={"reasoning_effort": "low"},
        )
        if text:
            return text
    grok = os.environ.get("XAI_API_KEY", "").strip()
    if grok:
        text = _openai_chat(
            route="grok",
            base="https://api.x.ai/v1",
            key=grok,
            # grok-3-mini is a retired alias xAI now serves via grok-4.3, a full
            # reasoning model. reasoning_effort=low measurably cuts its reasoning
            # spend (~11% fewer total tokens in our tests) with no quality loss.
            model=os.environ.get("GROK_MODEL", "grok-3-mini"),
            user=user,
            extra={"reasoning_effort": "low"},
        )
        if text:
            return text
    return None


def _user_payload(ctx: ViewerContext) -> str:
    last_public = ctx.public_log[-1].text if ctx.public_log else "(none yet)"
    own = " | ".join(e.text for e in ctx.own_private_events[-3:]) or "(none)"
    return (
        f"Anonymous group summary: {ctx.group_summary}\n"
        f"Latest public plan: {last_public}\n"
        f"This person's own private notes: {own}\n"
        "Write the whisper now."
    )


def _openai_chat(
    *,
    route: str,
    base: str,
    key: str,
    model: str,
    user: str,
    max_tokens: int = 120,
    extra: dict[str, Any] | None = None,
) -> str | None:
    url = base.rstrip("/") + "/chat/completions"
    body: dict[str, Any] = {
        "model": model,
        "temperature": 0.4,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
    }
    if extra:
        body.update(extra)
    try:
        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=12.0,
        )
    except httpx.HTTPError:
        log_tokens(route, model=model, ok=False)
        return None
    if response.status_code >= 400:
        log_tokens(route, model=model, ok=False)
        return None
    data = response.json()
    usage = data.get("usage") or {}
    completion_details = usage.get("completion_tokens_details") or {}
    log_tokens(
        route,
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        completion_tokens=int(usage.get("completion_tokens") or 0),
        reasoning_tokens=int(completion_details.get("reasoning_tokens") or 0),
        cost_usd_ticks=int(usage.get("cost_in_usd_ticks") or 0),
        model=model,
        ok=True,
    )
    choices = data.get("choices") or []
    if not choices:
        return None
    message = (choices[0].get("message") or {}).get("content") or ""
    text = str(message).strip().strip('"')
    return text or None
