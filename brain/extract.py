"""Turn a private event into structured constraints. Public events yield none."""

from __future__ import annotations

import re

from contracts.schema import Constraint, Event

from brain.privacy import DAYS, DAY_ABBREV, money_amounts, normalize_text

_HARD = re.compile(
    r"\b(can't|cannot|won't|will not|must not|have to|impossible|"
    r"no way|blocked|don't have|do not have|can't do|cannot do|"
    r"out on|out of town|unavailable|hard no|i'm out|im out|i am out)\b",
    re.I,
)
_SOFT = re.compile(
    r"\b(prefer|rather|would rather|if possible|maybe|kinda|kind of|"
    r"not a fan|would like|ideally|hoping|might|soft|leaning)\b",
    re.I,
)

_BUDGET_CUE = re.compile(
    r"\b(budget|afford|cap|spend|spending|dollars|bucks|\$|more than|"
    r"less than|under|broke|cheap|expensive)\b",
    re.I,
)
_BUDGET_FLOOR_ONLY = re.compile(
    r"\b(at least|minimum|no less than)\b",
    re.I,
)

_AVOID = re.compile(
    r"(?:avoid|not with|without|don't (?:invite|want|include)|"
    r"do not (?:invite|want|include)|rather not (?:go with|invite|see)|"
    r"can't stand|cannot stand)\s+([A-Za-z][A-Za-z'-]{1,19})",
    re.I,
)
_AVOID_STOP = frozenset(
    {
        "the",
        "a",
        "an",
        "large",
        "groups",
        "group",
        "that",
        "this",
        "him",
        "her",
        "them",
        "people",
        "anyone",
        "someone",
        "crowds",
        "going",
        "doing",
        "being",
        "expensive",
        "places",
        "it",
        "me",
        "us",
    }
)

_LOW_ENERGY = re.compile(
    r"\b(tired|exhausted|drained|low energy|no energy|wiped|"
    r"chill(?:er)? night|quiet night|take it easy|low[- ]key)\b",
    re.I,
)
_HIGH_ENERGY = re.compile(
    r"\b(high energy|wired|down for anything|hype|pumped|"
    r"lots of energy)\b",
    re.I,
)

_DATE_CUE = re.compile(
    r"\b(" + "|".join(DAYS) + r"|weekend|out on|blocked|can't do|cannot do|"
    r"unavailable|free on|busy)\b",
    re.I,
)


def _is_hard(text: str) -> bool:
    hard = bool(_HARD.search(text))
    soft = bool(_SOFT.search(text))
    if hard:
        return True
    if soft:
        return False
    return True


def _budget(user: str, text: str, hard: bool) -> list[Constraint]:
    if _BUDGET_FLOOR_ONLY.search(text) and not re.search(
        r"\b(under|below|at most|no more|not more|cap|max)\b", text, re.I
    ):
        return []
    if not _BUDGET_CUE.search(text) and not money_amounts(text):
        return []
    amounts = money_amounts(text)
    if not amounts:
        return []
    cap = min(amounts)
    return [
        Constraint(user=user, type="budget_cap", value=str(int(cap) if cap == int(cap) else cap), hard=hard)
    ]


def _dates(user: str, text: str, hard: bool) -> list[Constraint]:
    if not _DATE_CUE.search(text):
        return []
    # Availability ("I'm free Friday") is not a block.
    if re.search(r"\b(free|available|can do|down for)\b", text, re.I) and not _HARD.search(text):
        return []
    found: list[Constraint] = []
    if re.search(r"\bweekend\b", text, re.I):
        found.append(Constraint(user=user, type="date_block", value="weekend", hard=hard))
    for match in re.finditer(
        r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
        r"mon|tues?|wed|thurs?|thu|fri|sat|sun)\b",
        text,
        re.I,
    ):
        token = match.group(1).lower()
        day = DAY_ABBREV.get(token, token)
        found.append(Constraint(user=user, type="date_block", value=day, hard=hard))
    # Dedup while preserving order.
    seen: set[str] = set()
    unique: list[Constraint] = []
    for item in found:
        if item.value not in seen:
            seen.add(item.value)
            unique.append(item)
    return unique


def _avoid(user: str, text: str, hard: bool) -> list[Constraint]:
    found: list[Constraint] = []
    for match in _AVOID.finditer(text):
        name = match.group(1).strip(".,!?")
        if name.lower() in _AVOID_STOP:
            continue
        found.append(
            Constraint(user=user, type="avoid_person", value=name.lower(), hard=hard)
        )
    return found


def _energy(user: str, text: str, hard: bool) -> list[Constraint]:
    if _LOW_ENERGY.search(text):
        return [Constraint(user=user, type="energy", value="low", hard=hard)]
    if _HIGH_ENERGY.search(text):
        return [Constraint(user=user, type="energy", value="high", hard=hard)]
    return []


def extract_constraints(event: Event) -> list[Constraint]:
    """Turn a private event's text into structured constraints."""
    if not event.visibility.startswith("private:"):
        return []
    text = normalize_text(event.text)
    if not text:
        return []
    user = event.speaker
    hard = _is_hard(text)
    out: list[Constraint] = []
    out.extend(_budget(user, text, hard))
    out.extend(_dates(user, text, hard))
    out.extend(_avoid(user, text, hard))
    out.extend(_energy(user, text, hard))
    return out
