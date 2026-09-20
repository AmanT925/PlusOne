"""Call stream B in-process; fall back to stubs until Brain is implemented.

Brain currently raises NotImplementedError. The privacy boundary still runs
either way — stubs only see a ViewerContext from context_for.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from contracts.schema import Constraint, Event, ViewerContext

log = logging.getLogger("plusone.brain")

try:
    from brain.brain import (  # type: ignore
        direct_reply as _brain_direct_reply,
        extract_constraints as _brain_extract,
        group_summary as _brain_summary,
        looks_like_mention as _brain_mention,
        looks_like_proposal as _brain_proposal,
        should_whisper as _brain_should,
        wants_image as _brain_wants_image,
        write_whisper as _brain_write,
    )
except Exception:  # pragma: no cover - missing /brain during isolated tests
    _brain_extract = None
    _brain_summary = None
    _brain_write = None
    _brain_should = None
    _brain_proposal = None
    _brain_mention = None
    _brain_direct_reply = None
    _brain_wants_image = None


_BUDGET_RE = re.compile(r"\$\s*(\d{2,6})|(?:budget|afford|spend|cap)\D{0,12}(\d{2,6})", re.I)


def extract_constraints(event: Event) -> list[Constraint]:
    result = _try(_brain_extract, event)
    if result is not None:
        return result
    return _stub_extract(event)


def group_summary(constraints: list[Constraint]) -> str:
    result = _try(_brain_summary, constraints)
    if result is not None:
        return result
    return _stub_summary(constraints)


def write_whisper(viewer_context: ViewerContext) -> str:
    result = _try(_brain_write, viewer_context)
    if result is not None:
        return result
    return _stub_write(viewer_context)


def should_whisper(state: dict[str, Any]) -> bool:
    result = _try(_brain_should, state)
    if result is not None:
        return result
    return _stub_should(state)


def looks_like_proposal(text: str) -> bool:
    result = _try(_brain_proposal, text)
    if result is not None:
        return bool(result)
    t = (text or "").lower()
    return "let's" in t or "lets " in t or "resort" in t


def suggest_public(proposal: str, constraints) -> str | None:
    try:
        from brain.brain import suggest_public as _fn
    except Exception:
        _fn = None
    return _try(_fn, proposal, constraints)


def looks_like_mention(text: str) -> bool:
    result = _try(_brain_mention, text)
    if result is not None:
        return bool(result)
    return "plus one" in (text or "").lower() or "plusone" in (text or "").lower()


def direct_reply(proposal: str, constraints) -> str:
    result = _try(_brain_direct_reply, proposal, constraints)
    if result:
        return result
    return "Nothing's flagged yet — keep planning and I'll jump in if something looks off for someone."


def wants_image(text: str) -> bool:
    result = _try(_brain_wants_image, text)
    if result is not None:
        return bool(result)
    t = (text or "").lower()
    return any(w in t for w in ("image", "picture", "photo", "pic", "render", "visual"))


def _try(fn, *args):
    if fn is None:
        return None
    try:
        return fn(*args)
    except NotImplementedError:
        return None
    except Exception:
        log.exception("brain function %s failed; using stub", getattr(fn, "__name__", fn))
        return None


def _stub_extract(event: Event) -> list[Constraint]:
    if not str(event.visibility).startswith("private:"):
        return []
    match = _BUDGET_RE.search(event.text)
    if not match:
        return []
    amount = match.group(1) or match.group(2)
    return [
        Constraint(
            user=event.speaker,
            type="budget_cap",
            value=amount,
            hard=True,
        )
    ]


def _stub_summary(constraints: list[Constraint]) -> str:
    if not constraints:
        return "no private constraints yet"
    caps = []
    for c in constraints:
        if c.type == "budget_cap":
            try:
                caps.append(int(str(c.value).replace(",", "")))
            except ValueError:
                continue
    people = len({c.user for c in constraints})
    if caps:
        return f"budget ceiling is about ${min(caps)}; {people} people have shared constraints"
    return f"{people} people have shared private constraints"


def _stub_write(ctx: ViewerContext) -> str:
    summary = ctx.group_summary or "the group has some private constraints"
    if ctx.own_private_events:
        return (
            f"{summary}. I'll steer the group toward something that fits you "
            "without naming anyone."
        )
    last = ctx.public_log[-1].text if ctx.public_log else "the current plan"
    return f"Latest public note: {last}. {summary}."


def _stub_should(state: dict[str, Any]) -> bool:
    now = float(state.get("now") or 0)
    last = state.get("last_whisper_at")
    if last is not None and now - float(last) < 20:
        return False
    if state.get("trigger") == "private":
        return True
    return bool(state.get("has_private"))
