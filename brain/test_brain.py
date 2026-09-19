"""Brain tests — run from repo root: python -m unittest brain.test_brain"""

from __future__ import annotations

import re
import unittest

from contracts.schema import Event, ViewerContext

from brain.brain import (
    Plan,
    WhisperState,
    extract_constraints,
    group_summary,
    pick_plan,
    score_plan,
    should_whisper,
    token_report,
    write_whisper,
)
from brain.leak_harness import all_constraints, events_from, load_fixture, run_all, run_fixture
from brain.privacy import sentence_cap
from brain.timing import WHISPER_GAP_SECONDS, proposal_conflicts


def event(
    text: str,
    *,
    speaker: str = "sam",
    visibility: str | None = None,
    id: int = 1,
    ts: float = 1.0,
) -> Event:
    return Event(
        id=id,
        ts=ts,
        speaker=speaker,
        visibility=visibility or f"private:{speaker}",
        text=text,
    )


class ExtractTests(unittest.TestCase):
    def test_spec_budget_example(self) -> None:
        found = extract_constraints(event("I can't do more than 150 this month"))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].type, "budget_cap")
        self.assertEqual(found[0].value, "150")
        self.assertEqual(found[0].user, "sam")
        self.assertTrue(found[0].hard)

    def test_public_event_extracts_nothing(self) -> None:
        found = extract_constraints(
            event("I can't do more than 150 this month", visibility="public")
        )
        self.assertEqual(found, [])

    def test_date_block_saturday(self) -> None:
        found = extract_constraints(event("I'm out Saturday, that's a hard no."))
        types = {(item.type, item.value) for item in found}
        self.assertIn(("date_block", "saturday"), types)
        self.assertTrue(all(item.hard for item in found))

    def test_avoid_person(self) -> None:
        found = extract_constraints(event("Avoid Jordan, I'd rather not go with them."))
        people = [item for item in found if item.type == "avoid_person"]
        self.assertEqual(people[0].value, "jordan")

    def test_soft_budget(self) -> None:
        found = extract_constraints(
            event("I'd rather not spend more than 80 if possible")
        )
        self.assertEqual(found[0].type, "budget_cap")
        self.assertEqual(found[0].value, "80")
        self.assertFalse(found[0].hard)

    def test_energy_low(self) -> None:
        found = extract_constraints(event("I'm exhausted — keep it low key if possible"))
        self.assertTrue(any(item.type == "energy" and item.value == "low" for item in found))

    def test_multiple_constraints_one_utterance(self) -> None:
        found = extract_constraints(
            event("I can't do more than 40 and I'm out Friday")
        )
        kinds = {item.type for item in found}
        self.assertEqual(kinds, {"budget_cap", "date_block"})

    def test_curly_apostrophe(self) -> None:
        found = extract_constraints(event("I can’t do more than 150 this month"))
        self.assertEqual(found[0].value, "150")


class SummaryTests(unittest.TestCase):
    def test_anonymous_budget_ceiling(self) -> None:
        events = events_from(load_fixture("weekend_trip.json")["events"])
        summary = group_summary(all_constraints(events))
        self.assertIn("budget ceiling is about $150", summary)
        for name in ("sam", "priya", "maya", "alex"):
            self.assertIsNone(re.search(rf"\b{name}\b", summary, re.I))

    def test_empty(self) -> None:
        self.assertEqual(group_summary([]), "no shared constraints yet")


class WhisperTests(unittest.TestCase):
    def _weekend_ctx(self, viewer: str) -> ViewerContext:
        events = events_from(load_fixture("weekend_trip.json")["events"])
        public = [item for item in events if item.visibility == "public"]
        own = [item for item in events if item.visibility == f"private:{viewer}"]
        return ViewerContext(
            public_log=public,
            own_private_events=own,
            group_summary=group_summary(all_constraints(events)),
        )

    def test_two_sentences_max(self) -> None:
        text = write_whisper(self._weekend_ctx("sam"))
        self.assertLessEqual(len(re.findall(r"[.!?]+", text)), 2)
        self.assertEqual(sentence_cap(text, 2), text)

    def test_does_not_name_other_people(self) -> None:
        text = write_whisper(self._weekend_ctx("sam"))
        for name in ("priya", "maya", "alex"):
            self.assertIsNone(re.search(rf"\b{name}\b", text, re.I), text)

    def test_budget_conflict_nudge(self) -> None:
        text = write_whisper(self._weekend_ctx("sam")).lower()
        self.assertIn("cap", text)


class TimingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.constraints = extract_constraints(
            event("I can't do more than 150 this month")
        )
        self.proposal = "Let's do a cabin this weekend, like $300 each"

    def test_whisper_when_conflict_and_gap(self) -> None:
        self.assertTrue(
            should_whisper(
                WhisperState(
                    public_proposal=self.proposal,
                    viewer_constraints=self.constraints,
                    last_whisper_ts=0.0,
                    now=WHISPER_GAP_SECONDS,
                )
            )
        )

    def test_no_whisper_before_20s(self) -> None:
        self.assertFalse(
            should_whisper(
                WhisperState(
                    public_proposal=self.proposal,
                    viewer_constraints=self.constraints,
                    last_whisper_ts=100.0,
                    now=119.9,
                )
            )
        )

    def test_no_whisper_mid_sentence(self) -> None:
        self.assertFalse(
            should_whisper(
                WhisperState(
                    public_proposal=self.proposal,
                    viewer_constraints=self.constraints,
                    last_whisper_ts=None,
                    now=1000.0,
                    mid_sentence=True,
                )
            )
        )

    def test_no_whisper_without_conflict(self) -> None:
        self.assertFalse(
            should_whisper(
                {
                    "public_proposal": "Coffee for $8",
                    "viewer_constraints": self.constraints,
                    "last_whisper_ts": None,
                    "now": 1000.0,
                }
            )
        )

    def test_conflict_helper(self) -> None:
        hits = proposal_conflicts(self.proposal, self.constraints)
        self.assertTrue(hits)


class ScoringTests(unittest.TestCase):
    def test_hard_budget_fails_cabin(self) -> None:
        constraints = extract_constraints(event("I can't do more than 150 this month"))
        cabin = Plan(
            "weekend cabin trip",
            300.0,
            frozenset({"weekend", "saturday", "sunday"}),
            frozenset(),
            "high",
        )
        picnic = Plan("picnic in the park", 15.0, frozenset(), frozenset(), "low")
        self.assertEqual(score_plan(cabin, constraints), 0.0)
        self.assertGreater(score_plan(picnic, constraints), 0.0)

    def test_pick_plan_respects_caps(self) -> None:
        events = events_from(load_fixture("weekend_trip.json")["events"])
        constraints = all_constraints(events)
        plan = pick_plan(constraints, seed="weekend")
        self.assertIsNotNone(plan.cost)
        assert plan.cost is not None
        self.assertLessEqual(plan.cost, 150)
        self.assertNotIn("saturday", plan.days)
        self.assertNotEqual(plan.energy, "high")


class FixtureAndLeakTests(unittest.TestCase):
    def test_three_fixture_groups(self) -> None:
        from pathlib import Path

        names = sorted(path.name for path in (Path(__file__).resolve().parents[1] / "fixtures").glob("*.json"))
        self.assertEqual(names, ["dinner.json", "extraction_attacks.json", "weekend_trip.json"])

    def test_leak_harness_zero_leaks(self) -> None:
        rows = run_all()
        self.assertEqual(sum(row["leaks"] for row in rows), 0)
        self.assertGreater(sum(row["attempts"] for row in rows), 0)

    def test_weekend_fixture_extracts_four_people(self) -> None:
        events = events_from(load_fixture("weekend_trip.json")["events"])
        users = {item.user for item in all_constraints(events)}
        self.assertEqual(users, {"sam", "priya", "maya", "alex"})

    def test_token_report_compression_smaller(self) -> None:
        data = load_fixture("weekend_trip.json")
        events = events_from(data["events"])
        constraints = all_constraints(events)
        report = token_report(events, constraints, run_id="test")
        self.assertGreater(
            int(report["tokens_without_compression"]),
            int(report["tokens_with_compression"]),
        )

    def test_run_fixture_keys(self) -> None:
        row = run_fixture("dinner.json")
        self.assertEqual(row["leaks"], 0)
        self.assertIn("budget ceiling", row["summary"])


if __name__ == "__main__":
    unittest.main()
