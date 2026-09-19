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
        extract_constraints as _brain_extract,
        group_summary as _brain_summary,
        should_whisper as _brain_should,
        write_whisper as _brain_write,
    )
except Exception:  # pragma: no cover - missing /brain during isolated tests
    _brain_extract = None
    _brain_summary = None
    _brain_write = None
    _brain_should = None


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
