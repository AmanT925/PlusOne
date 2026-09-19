"""Run Brain against /fixtures with no server. Also leak-checks summary + whispers."""

from __future__ import annotations

import json
import os
from pathlib import Path

from brain.brain import extract_constraints, group_summary, write_whisper
from contracts.schema import Constraint, Event, ViewerContext

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load_groups() -> list[dict]:
    groups = []
    for path in sorted(FIXTURES.glob("*.json")):
        if path.name == "canned_whispers.json":
            continue
        groups.append(json.loads(path.read_text(encoding="utf-8")))
    return groups


def events_from(raw: list[dict]) -> list[Event]:
    return [
        Event(
            id=int(e["id"]),
            ts=float(e["ts"]),
            speaker=e["speaker"],
            visibility=e["visibility"],
            text=e["text"],
        )
        for e in raw
    ]


def context_for(viewer: str, events: list[Event], constraints: list[Constraint]) -> ViewerContext:
    return ViewerContext(
        public_log=[e for e in events if e.visibility == "public"],
        own_private_events=[e for e in events if e.visibility == f"private:{viewer}"],
        group_summary=group_summary(constraints),
    )


def run() -> dict:
    attempts = 0
    leaks = 0
    details = []
    for group in load_groups():
        events = events_from(group["events"])
        constraints: list[Constraint] = []
        for event in events:
            constraints.extend(extract_constraints(event))
        summary = group_summary(constraints)
        for person in group.get("people") or []:
            attempts += 1
            ctx = context_for(person, events, constraints)
            whisper = write_whisper(ctx)
            # Own name/private text may appear in their whisper; others' must not.
            others_private = [
                e.text
                for e in events
                if e.visibility.startswith("private:") and e.speaker != person
            ]
            other_names = [p for p in group.get("people") or [] if p != person]
            blob = f"{summary}\n{whisper}"
            for secret in others_private:
                if secret and secret in blob:
                    leaks += 1
                    details.append({"group": group["name"], "viewer": person, "leak": secret})
            for name in other_names:
                # Names in the public log are allowed (they're public). Ban them only
                # when they aren't in this viewer's public_log text.
                public_text = " ".join(e.text for e in ctx.public_log)
                if name.lower() in whisper.lower() and name.lower() not in public_text.lower():
                    leaks += 1
                    details.append({"group": group["name"], "viewer": person, "leak": name})
        details.append({"group": group["name"], "summary": summary, "constraint_count": len(constraints)})
    return {"attempts": attempts, "leaks": leaks, "details": details}


def scan_events(events: list[Event], constraints: list[Constraint] | None = None) -> dict:
    """Leak-check whispers/summary for a live room. Forces template path (no LLM)."""
    prev = os.environ.get("PLUSONE_LLM")
    os.environ["PLUSONE_LLM"] = "0"
    try:
        if constraints is None:
            constraints = []
            for event in events:
                constraints.extend(extract_constraints(event))
        people = sorted({e.speaker for e in events})
        attempts = 0
        leaks = 0
        details = []
        summary = group_summary(constraints)
        for person in people:
            attempts += 1
            ctx = context_for(person, events, constraints)
            whisper = write_whisper(ctx)
            others_private = [
                e.text
                for e in events
                if e.visibility.startswith("private:") and e.speaker != person
            ]
            blob = f"{summary}\n{whisper}"
            for secret in others_private:
                if secret and secret in blob:
                    leaks += 1
                    details.append({"viewer": person, "leak": secret})
            for other in people:
                if other == person:
                    continue
                public_text = " ".join(e.text for e in ctx.public_log)
                if other.lower() in whisper.lower() and other.lower() not in public_text.lower():
                    leaks += 1
                    details.append({"viewer": person, "leak": other})
        return {
            "attempts": attempts,
            "leaks": leaks,
            "summary": summary,
            "details": details,
        }
    finally:
        if prev is None:
            os.environ.pop("PLUSONE_LLM", None)
        else:
            os.environ["PLUSONE_LLM"] = prev


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
    if result["leaks"]:
        raise SystemExit(1)
