"""Stream B: Brain — constraint extraction, planning, whisper writing.

Signatures match contracts/schema.py. These are stubs: build order step 2 in
SPEC.md is to replace them with real logic, tested against /fixtures.
"""

from contracts.schema import Constraint, Event, ViewerContext


def extract_constraints(event: Event) -> list[Constraint]:
    """Turn a private event's text into structured constraints."""
    raise NotImplementedError


def group_summary(constraints: list[Constraint]) -> str:
    """Build the anonymous summary every whisper and public message is allowed to see."""
    raise NotImplementedError


def write_whisper(viewer_context: ViewerContext) -> str:
    """Write a one- or two-sentence whisper for one viewer."""
    raise NotImplementedError


def should_whisper(state) -> bool:
    """Decide whether a nudge would help right now (see SPEC.md 'When to whisper')."""
    raise NotImplementedError
