"""One- or two-sentence whisper. Only uses ViewerContext — never others' raw private events."""

from __future__ import annotations

from contracts.schema import Constraint, ViewerContext

from brain.extract import extract_constraints
from brain.privacy import (
    constraint_users,
    contains_user_name,
    latest_public_proposal,
    sentence_cap,
)
from brain.scoring import pick_plan
from brain.timing import proposal_conflicts


def _own_constraints(ctx: ViewerContext) -> list[Constraint]:
    found: list[Constraint] = []
    for event in ctx.own_private_events:
        found.extend(extract_constraints(event))
    return found


def _viewer(ctx: ViewerContext) -> str:
    if ctx.own_private_events:
        return ctx.own_private_events[-1].speaker
    return ""


def _nudge(conflicts: list[Constraint], alternative: str) -> str:
    kinds = {item.type for item in conflicts}
    if "budget_cap" in kinds:
        return (
            f"The current idea looks over your cap. {alternative} still fits what you asked for."
        )
    if "date_block" in kinds:
        return (
            f"That timing collides with a day you blocked. {alternative} keeps things moving without it."
        )
    if "avoid_person" in kinds:
        return (
            f"That plan includes someone you asked to skip. {alternative} stays aligned with what you told me."
        )
    if "energy" in kinds:
        return (
            f"That option is a lot given your energy. {alternative} is a calmer fit."
        )
    return f"The current idea fights a limit you set. {alternative} is a safer steer."


def write_whisper(viewer_context: ViewerContext) -> str:
    """Write a one- or two-sentence whisper for one viewer."""
    own = _own_constraints(viewer_context)
    proposal = latest_public_proposal(viewer_context.public_log)
    conflicts = proposal_conflicts(proposal, own)
    seed = proposal or viewer_context.group_summary
    alternative = pick_plan(own, seed=seed).label

    if conflicts:
        text = _nudge(conflicts, alternative)
    elif own:
        text = (
            f"You're clear on the current direction. I'll only nudge if it drifts past your limits."
        )
    else:
        text = (
            "I only nudge you about your own limits, and I won't quote anyone else's."
        )

    text = sentence_cap(text, 2)
    # Never name other people as constraint owners. The viewer's own name is
    # also unnecessary in a whisper to them.
    users = constraint_users(own)
    users.update({event.speaker.lower() for event in viewer_context.public_log})
    viewer = _viewer(viewer_context).lower()
    others = {user for user in users if user and user != viewer}
    if contains_user_name(text, others):
        text = sentence_cap(
            f"Stay with options that fit the group ceiling. {alternative} is a solid steer.",
            2,
        )
    return text
