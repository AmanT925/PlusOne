"""Privacy boundary: the only context a model is ever allowed to see.

No caller should pass raw private events from other people into Brain.
`context_for` is that filter — see SPEC.md "Privacy boundary".
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from contracts.schema import Constraint, Event, ViewerContext


def context_for(
    viewer: str,
    events: Sequence[Event],
    constraints: Sequence[Constraint],
    summarize: Callable[[list[Constraint]], str],
) -> ViewerContext:
    """Build the per-viewer bundle Brain's whisper writer may receive.

    Included:
      - every public event
      - this viewer's own private events
      - an anonymous group summary derived from *all* constraints

    Excluded:
      - anyone else's private events (never even handed to `summarize`
        as raw text — only structured Constraint objects, which the
        summarizer must anonymize)
    """
    public_log = [e for e in events if e.visibility == "public"]
    own_private_events = [
        e for e in events if e.visibility == f"private:{viewer}"
    ]
    group_summary = summarize(list(constraints))
    return ViewerContext(
        public_log=public_log,
        own_private_events=own_private_events,
        group_summary=group_summary,
    )


def public_model_inputs(
    events: Sequence[Event],
    constraints: Sequence[Constraint],
    summarize: Callable[[list[Constraint]], str],
) -> tuple[list[Event], str]:
    """What public speech to the table is allowed to see: public log + summary."""
    public_log = [e for e in events if e.visibility == "public"]
    return public_log, summarize(list(constraints))
