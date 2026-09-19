import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _disable_sponsor_apis(monkeypatch):
    """Keep unit tests offline unless a test opts in."""
    monkeypatch.setenv("PLUSONE_VOICE", "0")
    monkeypatch.setenv("PLUSONE_IMAGINE", "0")
