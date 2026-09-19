"""Shared parsing and leak guards. Names never belong in group-facing text."""

from __future__ import annotations

import re

from contracts.schema import Constraint, Event

_APOSTROPHES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})

DAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
DAY_ABBREV = {
    "mon": "monday",
    "tue": "tuesday",
    "tues": "tuesday",
    "wed": "wednesday",
    "thu": "thursday",
    "thur": "thursday",
    "thurs": "thursday",
    "fri": "friday",
    "sat": "saturday",
    "sun": "sunday",
}

_DAY_PATTERN = re.compile(
    r"\b("
    + "|".join(DAYS)
    + r"|mon|tues?|wed|thurs?|thu|fri|sat|sun|weekend)\b",
    re.I,
)

_MONEY = re.compile(
    r"\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)|"
    r"\b(\d{1,4}(?:\.\d{1,2})?)\s*(?:dollars|bucks|usd)\b|"
    r"\b(?:under|below|max(?:imum)?|cap(?:ped)?(?:\s+at)?|"
    r"budget(?:\s+(?:of|is|at))?|no more than|not more than|"
    r"more than|over|less than|at most|around|about)\s*\$?\s*"
    r"(\d{1,4}(?:\.\d{1,2})?)\b|"
    r"\b(\d{1,4}(?:\.\d{1,2})?)\s*(?:a head|each|per person)\b",
    re.I,
)

_HIGH_ENERGY = re.compile(
    r"\b(club|party|all-?nighter|rave|hike|cabin|concert|bar crawl|"
    r"intense|packed day|backpacking)\b",
    re.I,
)
_LOW_ENERGY = re.compile(
    r"\b(chill|quiet|low[- ]key|take it easy|movie night|stay in)\b",
    re.I,
)

_NAME_STOP = frozenset(
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
        "everybody",
        "everyone",
        "crowds",
        "crowd",
        "me",
        "us",
        "we",
        "it",
        "my",
        "our",
        "going",
        "doing",
        "being",
        "having",
        "expensive",
        "cheap",
        "places",
        "place",
        "weekend",
        "tonight",
        "today",
        "tomorrow",
        *DAYS,
    }
)


def normalize_text(text: str) -> str:
    return text.translate(_APOSTROPHES).strip()


def parse_amount(raw: str) -> float:
    return float(raw.replace(",", ""))


def money_amounts(text: str) -> list[float]:
    found: list[float] = []
    for match in _MONEY.finditer(text):
        for group in match.groups():
            if group:
                found.append(parse_amount(group))
                break
    return found


def mentioned_days(text: str) -> set[str]:
    days: set[str] = set()
    for match in _DAY_PATTERN.finditer(text):
        token = match.group(1).lower()
        if token == "weekend":
            days.update({"saturday", "sunday", "weekend"})
        else:
            days.add(DAY_ABBREV.get(token, token))
    return days


def mentioned_names(text: str) -> set[str]:
    names: set[str] = set()
    for match in re.finditer(r"\b([A-Z][a-z]{1,19})\b", text):
        word = match.group(1).lower()
        if word not in _NAME_STOP and word not in DAYS:
            names.add(word)
    for match in re.finditer(
        r"\b(?:invite|with|bring|include)\s+([A-Za-z][A-Za-z'-]{1,19})\b",
        text,
        re.I,
    ):
        word = match.group(1).lower().strip(".,!?")
        if word not in _NAME_STOP and word not in DAYS:
            names.add(word)
    return names


def public_energy(text: str) -> str:
    if _HIGH_ENERGY.search(text):
        return "high"
    if _LOW_ENERGY.search(text):
        return "low"
    return "medium"


def latest_public_proposal(events: list[Event]) -> str:
    publics = [event.text for event in events if event.visibility == "public"]
    return publics[-1] if publics else ""


def constraint_users(constraints: list[Constraint]) -> set[str]:
    return {c.user.lower() for c in constraints if c.user}


def contains_user_name(text: str, users: set[str]) -> bool:
    lowered = text.lower()
    for user in users:
        if user and re.search(rf"\b{re.escape(user)}\b", lowered):
            return True
    return False


def sentence_cap(text: str, limit: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = [part.strip() for part in parts if part.strip()][:limit]
    out = " ".join(kept).strip()
    if out and out[-1] not in ".!?":
        out += "."
    return out
