"""Token counts for The Token Company (product calls, not coding)."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

LOG = Path(__file__).resolve().parents[1] / "brain" / "token_log.jsonl"
_lock = threading.Lock()


@dataclass
class TokenRecord:
    ts: float
    route: str  # muse | grok | regex
    prompt_tokens: int
    completion_tokens: int
    model: str
    ok: bool
    reasoning_tokens: int = 0
    cost_usd_ticks: int = 0


_records: list[TokenRecord] = []


def log_tokens(
    route: str,
    *,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    model: str = "",
    ok: bool = True,
    reasoning_tokens: int = 0,
    cost_usd_ticks: int = 0,
) -> None:
    rec = TokenRecord(
        ts=time.time(),
        route=route,
        prompt_tokens=int(prompt_tokens or 0),
        completion_tokens=int(completion_tokens or 0),
        model=model,
        ok=ok,
        reasoning_tokens=int(reasoning_tokens or 0),
        cost_usd_ticks=int(cost_usd_ticks or 0),
    )
    with _lock:
        _records.append(rec)
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(rec)) + "\n")


def totals() -> dict[str, dict[str, int]]:
    by: dict[str, dict[str, int]] = {}
    with _lock:
        rows = list(_records)
    for rec in rows:
        bucket = by.setdefault(
            rec.route,
            {
                "calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "reasoning_tokens": 0,
                "cost_usd_ticks": 0,
            },
        )
        bucket["calls"] += 1
        bucket["prompt_tokens"] += rec.prompt_tokens
        bucket["completion_tokens"] += rec.completion_tokens
        bucket["reasoning_tokens"] += rec.reasoning_tokens
        bucket["cost_usd_ticks"] += rec.cost_usd_ticks
    return by


def reset() -> None:
    with _lock:
        _records.clear()
