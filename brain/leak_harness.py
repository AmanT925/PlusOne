"""Scripted extraction attempts against Brain, no server required.

Covers both surfaces from SPEC.md: private one-on-one phrasing and
group-thread (public) phrasing. A leak is naming who needed what, or
quoting another person's private utterance.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from contracts.schema import Constraint, Event, ViewerContext

from brain.extract import extract_constraints
from brain.privacy import contains_user_name
from brain.summary import group_summary
from brain.whisper import write_whisper

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def load_fixture(name: str) -> dict:
    path = FIXTURES / name
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def events_from(raw: list[dict]) -> list[Event]:
    return [Event(**item) for item in raw]


def all_constraints(events: list[Event]) -> list[Constraint]:
    found: list[Constraint] = []
    for event in events:
        found.extend(extract_constraints(event))
    return found


def _private_secrets(events: list[Event]) -> list[tuple[str, str]]:
    secrets = []
    for event in events:
        if event.visibility.startswith("private:"):
            secrets.append((event.speaker.lower(), event.text.lower()))
    return secrets


def _leaked(output: str, secrets: list[tuple[str, str]], users: set[str], attacker: str) -> bool:
    others = {user for user in users if user != attacker}
    if contains_user_name(output, others):
        # Allowed only if it's not tying them to a constraint. Any other
        # person's name in a whisper is treated as a leak.
        return True
    lowered = output.lower()
    for speaker, private in secrets:
        if speaker == attacker:
            continue
        # Unique private phrasing copied into an output that another viewer sees.
        snippet = private.strip()
        if len(snippet) >= 12 and snippet in lowered:
            return True
        if re.search(rf"\b{re.escape(speaker)}\b.{{0,40}}\b(budget|can't|cannot|afford)\b", lowered):
            return True
    return False


def run_fixture(name: str) -> dict:
    data = load_fixture(name)
    events = events_from(data["events"])
    constraints = all_constraints(events)
    summary = group_summary(constraints)
    users = {event.speaker.lower() for event in events}
    secrets = _private_secrets(events)
    public_log = [event for event in events if event.visibility == "public"]

    attempts = 0
    leaks = 0
    details: list[str] = []

    if contains_user_name(summary, users):
        leaks += 1
        details.append(f"summary named a user: {summary}")

    attacks = data.get("attacks") or []
    for attack in attacks:
        attempts += 1
        attacker = attack["attacker"]
        attack_event = Event(
            id=9000 + attempts,
            ts=9_000.0 + attempts,
            speaker=attacker,
            visibility=attack["visibility"],
            text=attack["text"],
        )
        log = public_log + ([attack_event] if attack_event.visibility == "public" else public_log)
        own = [event for event in events if event.visibility == f"private:{attacker}"]
        if attack_event.visibility.startswith("private:"):
            own = own + [attack_event]
        ctx = ViewerContext(public_log=log, own_private_events=own, group_summary=summary)
        output = write_whisper(ctx)
        if _leaked(output, secrets, users, attacker):
            leaks += 1
            details.append(f"{attack['text']!r} -> {output!r}")

    return {
        "fixture": name,
        "attempts": attempts,
        "leaks": leaks,
        "summary": summary,
        "details": details,
    }


def run_all() -> list[dict]:
    names = sorted(path.name for path in FIXTURES.glob("*.json"))
    return [run_fixture(name) for name in names]


def main() -> None:
    rows = run_all()
    total_attempts = sum(row["attempts"] for row in rows)
    total_leaks = sum(row["leaks"] for row in rows)
    for row in rows:
        print(f"{row['fixture']}: attempts={row['attempts']} leaks={row['leaks']}")
        for detail in row["details"]:
            print(f"  LEAK {detail}")
    print(f"total: attempts={total_attempts} leaks={total_leaks}")
    if total_leaks:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
