"""Anonymous group summary. Never includes who needed what."""

from __future__ import annotations

from contracts.schema import Constraint

from brain.privacy import constraint_users, contains_user_name, parse_amount


def _budget_line(constraints: list[Constraint]) -> str | None:
    caps: list[float] = []
    for item in constraints:
        if item.type != "budget_cap":
            continue
        try:
            caps.append(parse_amount(item.value))
        except ValueError:
            continue
    if not caps:
        return None
    ceiling = min(caps)
    as_int = int(ceiling)
    shown = as_int if as_int == ceiling else ceiling
    return f"budget ceiling is about ${shown}"


def _date_line(constraints: list[Constraint]) -> str | None:
    days = [item.value for item in constraints if item.type == "date_block"]
    if not days:
        return None
    unique = list(dict.fromkeys(days))
    if len(unique) == 1:
        return f"{unique[0]} is blocked"
    return "blocked dates: " + ", ".join(unique)


def _avoid_line(constraints: list[Constraint]) -> str | None:
    people = [item.value for item in constraints if item.type == "avoid_person"]
    if not people:
        return None
    unique = list(dict.fromkeys(people))
    return "plans should not include " + ", ".join(unique)


def _energy_line(constraints: list[Constraint]) -> str | None:
    energies = {item.value for item in constraints if item.type == "energy"}
    if not energies:
        return None
    if "low" in energies:
        return "keep options on the calmer side"
    if "high" in energies:
        return "higher-energy options are welcome"
    return None


def group_summary(constraints: list[Constraint]) -> str:
    """Build the anonymous summary every whisper and public message is allowed to see."""
    if not constraints:
        return "no shared constraints yet"
    parts = [
        line
        for line in (
            _budget_line(constraints),
            _date_line(constraints),
            _avoid_line(constraints),
            _energy_line(constraints),
        )
        if line
    ]
    text = "; ".join(parts) if parts else "no shared constraints yet"
    users = constraint_users(constraints)
    if contains_user_name(text, users):
        raise AssertionError("group_summary leaked a user name")
    return text
