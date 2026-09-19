"""Stream B: Brain — constraint extraction, planning, whisper writing.

Signatures match contracts/schema.py. Test against /fixtures; stream A
imports these functions in-process at the text-loop integration.
"""

from brain.extract import extract_constraints
from brain.scoring import Plan, pick_plan, pick_plans, score_plan
from brain.summary import group_summary
from brain.timing import WhisperState, should_whisper
from brain.tokens import token_report
from brain.whisper import write_whisper

__all__ = [
    "extract_constraints",
    "group_summary",
    "write_whisper",
    "should_whisper",
    "WhisperState",
    "Plan",
    "score_plan",
    "pick_plan",
    "pick_plans",
    "token_report",
]
