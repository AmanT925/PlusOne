"""Stream B: Brain — constraint extraction, planning, whisper writing.

Plain functions. No server. Signatures match contracts/schema.py.
"""

from __future__ import annotations

import re
from typing import Any

from contracts.schema import Constraint, Event, ViewerContext

from brain.llm import complete_whisper
from brain.tokens import log_tokens

CANDIDATE_PLANS = [
    {"name": "picnic", "cost": 40, "intensity": "low", "blurb": "a picnic or BYO hang for about $40"},
    {"name": "casual", "cost": 80, "intensity": "low", "blurb": "a casual dinner around $80 a head"},
    {"name": "mid", "cost": 140, "intensity": "med", "blurb": "a mid-range option around $140 that should clear the group ceiling"},
    {"name": "resort", "cost": 400, "intensity": "high", "blurb": "the fancy resort"},
]

_BUDGET_RE = re.compile(
    r"(?:\$\s*(\d{2,6}))|(?:(?:budget|afford|spend|cap|more than|max(?:imum)?)\D{0,16}(\d{2,6}))",
    re.I,
)
_DATE_RE = re.compile(
    r"(can't|cannot|won't|not (?:free|available)|busy|blocked).{0,40}"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday|weekend|"
    r"next week|this week|tonight|\d{1,2}/\d{1,2})",
    re.I,
)
_AVOID_RE = re.compile(
    r"(?:avoid|can't stand|not with|room with|be with)\s+([A-Za-z]{2,})",
    re.I,
)
_ENERGY_LOW = re.compile(r"\b(exhausted|tired|drained|low energy|need a quiet)\b", re.I)
_ENERGY_HIGH = re.compile(r"\b(high energy|pumped|down for anything|lots of energy)\b", re.I)
_HARD = re.compile(r"\b(can't|cannot|won't|hard no|must not|impossible)\b", re.I)


_PROPOSAL_CUE = re.compile(
    r"\b(let['’]?s|how about|we should|i vote|go with|book the|do the)\b",
    re.I,
)
_PROPOSAL_VENUE = re.compile(
    r"\b(resort|hotel|club|steak|tasting|spa)\b",
    re.I,
)
_TRAVEL_RE = re.compile(
    r"\b(switzerland|swiss|europe|paris|tokyo|hawaii|mexico|canada|iceland|"
    r"ski(?:ing)?|alps|flight|flights|vacation|getaway|abroad|overseas|"
    r"trip to|fly to)\b",
    re.I,
)
_CONSTRAINT_CUE = re.compile(
    r"\b(can't|cannot|won't|afford|budget|more than|cap|max(?:imum)?)\b",
    re.I,
)


def looks_like_proposal(text: str) -> bool:
    """True for table-talk plans (resort, trip, Switzerland), not private caps."""
    t = (text or "").strip()
    if not t:
        return False
    cue = bool(_PROPOSAL_CUE.search(t))
    venue = bool(_PROPOSAL_VENUE.search(t))
    travel = bool(_TRAVEL_RE.search(t))
    if _CONSTRAINT_CUE.search(t) and not cue and not venue:
        return False
    if cue or venue or travel:
        return True
    return bool(re.search(r"[$＄]\s*\d{2,6}", t) and re.search(r"\b(let|plan|book|go)\b", t, re.I))


def extract_constraints(event: Event) -> list[Constraint]:
    if not str(event.visibility).startswith("private:"):
        return []
    text = event.text.strip()
    if looks_like_proposal(text):
        return []
    if not text:
        return []
    hard = bool(_HARD.search(text))
    found: list[Constraint] = []

    budget = _BUDGET_RE.search(text)
    if budget:
        amount = budget.group(1) or budget.group(2)
        found.append(
            Constraint(user=event.speaker, type="budget_cap", value=amount, hard=hard or True)
        )

    date = _DATE_RE.search(text)
    if date:
        found.append(
            Constraint(
                user=event.speaker,
                type="date_block",
                value=date.group(2).lower(),
                hard=hard,
            )
        )

    avoid = _AVOID_RE.search(text)
    if avoid:
        found.append(
            Constraint(
                user=event.speaker,
                type="avoid_person",
                value=avoid.group(1),
                hard=True,
            )
        )

    if _ENERGY_LOW.search(text):
        found.append(
            Constraint(user=event.speaker, type="energy", value="low", hard=False)
        )
    elif _ENERGY_HIGH.search(text):
        found.append(
            Constraint(user=event.speaker, type="energy", value="high", hard=False)
        )

    return found


def group_summary(constraints: list[Constraint]) -> str:
    """Anonymous: never include a speaker name or a unique fingerprint of one person."""
    if not constraints:
        return "no private constraints yet"

    people = len({c.user for c in constraints})
    parts: list[str] = []

    caps: list[int] = []
    for c in constraints:
        if c.type == "budget_cap":
            try:
                caps.append(int(str(c.value).replace(",", "").replace("$", "")))
            except ValueError:
                continue
    if caps:
        # Tightest ceiling, not whose it is.
        parts.append(f"budget ceiling is about ${min(caps)}")

    if any(c.type == "date_block" for c in constraints):
        parts.append("some dates are blocked for the group")

    if any(c.type == "avoid_person" for c in constraints):
        parts.append("the group has people-to-avoid constraints")

    energies = {c.value for c in constraints if c.type == "energy"}
    if energies == {"low"}:
        parts.append("energy is on the low side")
    elif energies:
        parts.append("energy in the group is mixed")

    if not parts:
        parts.append("private constraints are in play")

    parts.append(f"{people} people have shared constraints")
    return "; ".join(parts)


def write_whisper(viewer_context: ViewerContext) -> str:
    llm = complete_whisper(viewer_context)
    if llm:
        clipped = _clip_whisper(llm)
        if clipped:
            return clipped
    log_tokens("regex", model="template", ok=True)
    return _template_whisper(viewer_context)


def _template_whisper(viewer_context: ViewerContext) -> str:
    summary = viewer_context.group_summary or "the group has private constraints"
    last_public = (
        viewer_context.public_log[-1].text if viewer_context.public_log else "the current plan"
    )
    own = viewer_context.own_private_events[-1].text if viewer_context.own_private_events else ""
    if own:
        return (
            f"The current public plan may not fit the group ceiling. {summary}. "
            "I'll steer toward something cheaper without naming anyone."
        )
    return f"Latest public note: {last_public}. {summary}."


def _clip_whisper(text: str) -> str:
    text = " ".join(text.split())
    parts = []
    buf = ""
    for ch in text:
        buf += ch
        if ch in ".!?" and len(buf.strip()) > 8:
            parts.append(buf.strip())
            buf = ""
            if len(parts) >= 2:
                break
    if not parts:
        return text[:280].strip()
    return " ".join(parts)


def suggest_public(proposal: str, constraints: list[Constraint]) -> str | None:
    """Table-safe line from public proposal + anonymous constraints only."""
    if not proposal or not constraints:
        return None
    fake_state = {
        "public_proposal": proposal,
        "viewer_constraints": constraints,
        "has_private": True,
    }
    if not _conflicts(fake_state):
        implied_expensive = bool(_PROPOSAL_VENUE.search(proposal) or _TRAVEL_RE.search(proposal))
        has_limits = any(c.type in ("budget_cap", "energy", "date_block") for c in constraints)
        if not (implied_expensive and has_limits):
            return None
    plan = pick_plan(CANDIDATE_PLANS, constraints)
    if not plan:
        return None
    mentioned = [int(x) for x in re.findall(r"[$＄]\s*(\d{2,6})", proposal)]
    if mentioned and plan.get("cost") and int(plan["cost"]) >= max(mentioned):
        cheaper = [p for p in CANDIDATE_PLANS if p["cost"] < max(mentioned)]
        if cheaper:
            plan = pick_plan(cheaper, constraints) or cheaper[0]
    summary = group_summary(constraints)
    if _TRAVEL_RE.search(proposal):
        return (
            f"{summary}. A far trip like that is likely over the group ceiling. "
            f"How about {plan['blurb']} instead? That should fit everyone without calling anyone out."
        )
    return (
        f"{summary}. How about {plan['blurb']} instead? "
        "That should fit everyone without calling anyone out."
    )


def should_whisper(state: Any) -> bool:
    if not isinstance(state, dict):
        return False
    if state.get("mid_sentence"):
        return False
    if state.get("trigger") == "private":
        return True
    now = float(state.get("now") or 0)
    last = state.get("last_whisper_at")
    if last is not None and now - float(last) < 20:
        return False
    if not state.get("has_private"):
        return False
    return _conflicts(state)


def _conflicts(state: dict[str, Any]) -> bool:
    proposal = str(state.get("public_proposal") or "")
    constraints = state.get("viewer_constraints") or []
    if not proposal:
        return False
    dollars = re.findall(r"[$＄]\s*(\d{2,6})", proposal)
    if not dollars:
        dollars = re.findall(r"\b(\d{3,6})\s*(?:dollar|buck|resort|dinner|hotel)", proposal, re.I)
    for c in constraints:
        if getattr(c, "type", None) == "budget_cap" and dollars:
            try:
                if int(dollars[-1]) > int(str(c.value).replace("$", "")):
                    return True
            except ValueError:
                pass
        if getattr(c, "type", None) == "avoid_person" and str(c.value).lower() in proposal.lower():
            return True
        if getattr(c, "type", None) == "date_block" and str(c.value).lower() in proposal.lower():
            return True
    return False


def score_plan(plan: dict[str, Any], constraints: list[Constraint]) -> float:
    """Higher is a better fit. Used to pick a public suggestion that isn't a fingerprint."""
    score = 1.0
    cost = plan.get("cost")
    people = [str(p).lower() for p in plan.get("people") or []]
    when = str(plan.get("when") or "").lower()
    for c in constraints:
        if c.type == "budget_cap" and cost is not None:
            try:
                cap = int(str(c.value).replace("$", ""))
                if cost > cap:
                    score -= 2.0 if c.hard else 0.5
                else:
                    score += 0.3
            except ValueError:
                pass
        if c.type == "avoid_person" and c.value.lower() in people:
            score -= 3.0 if c.hard else 1.0
        if c.type == "date_block" and c.value.lower() in when:
            score -= 1.5 if c.hard else 0.5
        if c.type == "energy" and c.value == "low" and plan.get("intensity") == "high":
            score -= 0.4
    return score


def pick_plan(plans: list[dict[str, Any]], constraints: list[Constraint]) -> dict[str, Any] | None:
    """Prefer the nicest plan that still fits, not the cheapest every time."""
    if not plans:
        return None
    ranked = sorted(
        plans,
        key=lambda p: (score_plan(p, constraints), int(p.get("cost") or 0)),
        reverse=True,
    )
    chosen = dict(ranked[0])
    if len(ranked) > 1:
        chosen["alternates"] = [ranked[1].get("name")]
    return chosen
