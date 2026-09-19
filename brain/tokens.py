"""Token counts with and without compression (group summary vs raw constraints)."""

from __future__ import annotations

import json
from pathlib import Path

from contracts.schema import Constraint, Event

from brain.summary import group_summary

LOG_PATH = Path(__file__).resolve().parent / ".token_log.jsonl"


def estimate_tokens(text: str) -> int:
    words = text.split()
    return max(0, len(words))


def uncompressed_blob(events: list[Event], constraints: list[Constraint]) -> str:
    event_text = "\n".join(f"{event.speaker}: {event.text}" for event in events)
    constraint_text = "\n".join(
        f"{item.user} {item.type} {item.value} hard={item.hard}" for item in constraints
    )
    return event_text + "\n" + constraint_text


def compressed_blob(events: list[Event], constraints: list[Constraint]) -> str:
    public = [event for event in events if event.visibility == "public"]
    public_text = "\n".join(event.text for event in public)
    return public_text + "\n" + group_summary(constraints)


def token_report(
    events: list[Event],
    constraints: list[Constraint],
    *,
    run_id: str = "local",
    persist: bool = False,
) -> dict[str, int | str]:
    raw = uncompressed_blob(events, constraints)
    compact = compressed_blob(events, constraints)
    report: dict[str, int | str] = {
        "run_id": run_id,
        "tokens_without_compression": estimate_tokens(raw),
        "tokens_with_compression": estimate_tokens(compact),
    }
    if persist:
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(report) + "\n")
    return report
