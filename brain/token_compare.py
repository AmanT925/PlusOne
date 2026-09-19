"""Compare regex vs LLM token use on fixture groups. Does not print secrets."""

from __future__ import annotations

import json
import os

from brain.leak_test import context_for, events_from, load_groups
from brain.brain import extract_constraints, group_summary, write_whisper
from brain.tokens import reset, totals


def main() -> None:
    reset()
    os.environ["PLUSONE_LLM"] = "0"
    for group in load_groups():
        events = events_from(group["events"])
        constraints = []
        for event in events:
            constraints.extend(extract_constraints(event))
        summary = group_summary(constraints)
        for person in group.get("people") or []:
            write_whisper(context_for(person, events, constraints))
        _ = summary
    regex = totals()
    reset()
    os.environ["PLUSONE_LLM"] = "1"
    for group in load_groups():
        events = events_from(group["events"])
        constraints = []
        for event in events:
            constraints.extend(extract_constraints(event))
        for person in group.get("people") or []:
            write_whisper(context_for(person, events, constraints))
    llm = totals()
    print(json.dumps({"regex_path": regex, "llm_path": llm}, indent=2))


if __name__ == "__main__":
    main()
