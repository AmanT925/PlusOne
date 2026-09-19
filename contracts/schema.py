"""Frozen contracts shared by /server (stream A) and /brain (stream B).

See contracts/README.md before changing anything here — it needs all three
stream owners to agree first.
"""

from dataclasses import dataclass
from typing import Literal

ConstraintType = Literal["budget_cap", "date_block", "avoid_person", "energy"]


@dataclass(frozen=True)
class Event:
    id: int
    ts: float
    speaker: str
    visibility: str  # "public" or "private:<user>"
    text: str


@dataclass(frozen=True)
class Constraint:
    user: str
    type: ConstraintType
    value: str
    hard: bool


@dataclass(frozen=True)
class ViewerContext:
    """What context_for(viewer) builds: the only thing a model is ever given."""
    public_log: list[Event]
    own_private_events: list[Event]
    group_summary: str


# Stream B (Brain) exposes these to stream A (Core). Signatures are the contract;
# implementations live in /brain.
#
#   extract_constraints(event: Event) -> list[Constraint]
#   group_summary(constraints: list[Constraint]) -> str
#   write_whisper(viewer_context: ViewerContext) -> str
#   should_whisper(state) -> bool
