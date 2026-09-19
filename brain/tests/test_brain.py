import json
from pathlib import Path

from brain.brain import extract_constraints, group_summary, score_plan, should_whisper, write_whisper
from brain.leak_test import events_from, run
from contracts.schema import Constraint, Event, ViewerContext

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def test_weekend_trip_extracts_expected_types():
    group = json.loads((FIXTURES / "weekend_trip.json").read_text(encoding="utf-8"))
    events = events_from(group["events"])
    found = []
    for event in events:
        found.extend(extract_constraints(event))
    types = {(c.user, c.type) for c in found}
    assert ("sam", "budget_cap") in types
    assert ("priya", "avoid_person") in types
    summary = group_summary(found)
    assert "sam" not in summary.lower()
    assert "priya" not in summary.lower()
    assert "150" in summary


def test_whisper_only_uses_viewer_context():
    ctx = ViewerContext(
        public_log=[Event(1, 1, "alex", "public", "fancy resort")],
        own_private_events=[Event(2, 2, "sam", "private:sam", "cap $150")],
        group_summary="budget ceiling is about $150; 1 people have shared constraints",
    )
    text = write_whisper(ctx)
    assert "priya" not in text.lower()
    assert len(text) > 10


def test_should_whisper_timing_and_conflict():
    now = 100.0
    cap = Constraint(user="sam", type="budget_cap", value="150", hard=True)
    assert should_whisper(
        {
            "trigger": "public",
            "has_private": True,
            "now": now,
            "last_whisper_at": None,
            "public_proposal": "Let's do the $400 resort",
            "viewer_constraints": [cap],
            "mid_sentence": False,
        }
    )
    assert not should_whisper(
        {
            "trigger": "public",
            "has_private": True,
            "now": now,
            "last_whisper_at": 90.0,
            "public_proposal": "Let's do the $400 resort",
            "viewer_constraints": [cap],
        }
    )
    assert not should_whisper({"trigger": "private", "now": now, "mid_sentence": True})


def test_score_plan_penalizes_over_budget():
    constraints = [Constraint(user="sam", type="budget_cap", value="150", hard=True)]
    cheap = score_plan({"name": "picnic", "cost": 40}, constraints)
    fancy = score_plan({"name": "resort", "cost": 400}, constraints)
    assert cheap > fancy


def test_leak_harness_zero_leaks():
    result = run()
    assert result["leaks"] == 0
    assert result["attempts"] >= 4
