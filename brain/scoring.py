"""Score candidate plans against everyone's constraints.

Inference-leak rule: never pick a plan whose only advantage is being
exactly one person's number. Prefer a small set of fitting options.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from contracts.schema import Constraint

from brain.privacy import parse_amount

HARD_FAIL = 0.0


@dataclass(frozen=True)
class Plan:
    label: str
    cost: float | None
    days: frozenset[str]
    people: frozenset[str]
    energy: str  # low | medium | high


DEFAULT_CANDIDATES: tuple[Plan, ...] = (
    Plan("picnic in the park", 15.0, frozenset(), frozenset(), "low"),
    Plan("coffee and a walk", 12.0, frozenset(), frozenset(), "low"),
    Plan("casual taco dinner", 25.0, frozenset(), frozenset(), "medium"),
    Plan("weeknight dumplings", 30.0, frozenset({"wednesday"}), frozenset(), "medium"),
    Plan("board-game night in", 10.0, frozenset(), frozenset(), "low"),
    Plan("neighborhood pizza", 40.0, frozenset(), frozenset(), "medium"),
    Plan("mid-range group dinner", 75.0, frozenset(), frozenset(), "medium"),
    Plan("nice but not fancy dinner", 120.0, frozenset(), frozenset(), "medium"),
    Plan("concert tickets", 140.0, frozenset({"friday"}), frozenset(), "high"),
    Plan("weekend cabin trip", 300.0, frozenset({"weekend", "saturday", "sunday"}), frozenset(), "high"),
    Plan("club night", 80.0, frozenset({"saturday"}), frozenset(), "high"),
)


def _budget_cap(item: Constraint) -> float | None:
    if item.type != "budget_cap":
        return None
    try:
        return parse_amount(item.value)
    except ValueError:
        return None


def score_plan(plan: Plan, constraints: list[Constraint]) -> float:
    """Return 0.0 if any hard constraint fails, else a 0-1 fitness score."""
    if not constraints:
        return 0.5
    score = 1.0
    hard_hits = 0
    soft_hits = 0
    checks = 0
    for item in constraints:
        checks += 1
        ok = True
        if item.type == "budget_cap" and plan.cost is not None:
            cap = _budget_cap(item)
            if cap is not None:
                ok = plan.cost <= cap
        elif item.type == "date_block":
            block = item.value.lower()
            ok = block not in plan.days
            if block == "weekend":
                ok = not plan.days.intersection({"weekend", "saturday", "sunday"})
        elif item.type == "avoid_person":
            ok = item.value.lower() not in plan.people
        elif item.type == "energy":
            if item.value == "low" and plan.energy == "high":
                ok = False
            elif item.value == "high" and plan.energy == "low":
                ok = False
        if not ok:
            if item.hard:
                hard_hits += 1
            else:
                soft_hits += 1
    if hard_hits:
        return HARD_FAIL
    if checks:
        score -= 0.2 * soft_hits
    return max(0.01, min(1.0, score))


def _variety_key(label: str, seed: str) -> str:
    return sha256(f"{seed}::{label}".encode()).hexdigest()


def pick_plans(
    constraints: list[Constraint],
    *,
    seed: str = "",
    candidates: tuple[Plan, ...] = DEFAULT_CANDIDATES,
    k: int = 3,
) -> list[Plan]:
    """Return up to k fitting plans, shuffled stably so one person's cap
    is not the only visible reason a price moved.
    """
    ranked = sorted(
        ((score_plan(plan, constraints), plan) for plan in candidates),
        key=lambda pair: (-pair[0], _variety_key(pair[1].label, seed)),
    )
    fitting = [plan for score, plan in ranked if score > HARD_FAIL]
    if not fitting:
        fitting = [plan for _, plan in ranked]
    return fitting[:k]


def pick_plan(constraints: list[Constraint], *, seed: str = "") -> Plan:
    return pick_plans(constraints, seed=seed, k=1)[0]
