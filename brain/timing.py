"""When to whisper: conflict, not mid-sentence, ~20s since last whisper."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

from contracts.schema import Constraint

from brain.privacy import money_amounts, mentioned_days, mentioned_names, public_energy

WHISPER_GAP_SECONDS = 20.0


@dataclass
class WhisperState:
    """Shape stream A should pass into should_whisper.

    Not frozen in contracts/schema.py — this lives with Brain so Core can
    import it at the text-loop integration without changing the freeze.
    """

    public_proposal: str = ""
    viewer_constraints: list[Constraint] = field(default_factory=list)
    last_whisper_ts: float | None = None
    now: float = 0.0
    mid_sentence: bool = False
    speaking: bool = False  # alias some callers may use

    @classmethod
    def from_any(cls, state: Any) -> "WhisperState":
        if isinstance(state, cls):
            return state
        if isinstance(state, dict):
            allowed = {item.name for item in fields(cls)}
            return cls(**{key: value for key, value in state.items() if key in allowed})
        kwargs = {}
        for item in fields(cls):
            if hasattr(state, item.name):
                kwargs[item.name] = getattr(state, item.name)
        return cls(**kwargs)


def proposal_conflicts(proposal: str, constraints: list[Constraint]) -> list[Constraint]:
    if not proposal.strip() or not constraints:
        return []
    amounts = money_amounts(proposal)
    peak = max(amounts) if amounts else None
    days = mentioned_days(proposal)
    people = mentioned_names(proposal)
    energy = public_energy(proposal)
    hits: list[Constraint] = []
    for item in constraints:
        if item.type == "budget_cap" and peak is not None:
            try:
                cap = float(item.value)
            except ValueError:
                continue
            if peak > cap:
                hits.append(item)
        elif item.type == "date_block":
            block = item.value.lower()
            if block in days or (block == "weekend" and days.intersection({"saturday", "sunday", "weekend"})):
                hits.append(item)
        elif item.type == "avoid_person":
            if item.value.lower() in people:
                hits.append(item)
        elif item.type == "energy" and item.value == "low" and energy == "high":
            hits.append(item)
    return hits


def should_whisper(state: Any) -> bool:
    """Decide whether a nudge would help right now."""
    parsed = WhisperState.from_any(state)
    if parsed.mid_sentence or parsed.speaking:
        return False
    last = parsed.last_whisper_ts
    if last is not None and parsed.now - last < WHISPER_GAP_SECONDS:
        return False
    return bool(proposal_conflicts(parsed.public_proposal, parsed.viewer_constraints))
