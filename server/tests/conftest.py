import os
import sys
from pathlib import Path

os.environ["PLUSONE_LLM"] = "0"
os.environ["PLUSONE_IMAGINE"] = "0"
os.environ["PLUSONE_TTS"] = "0"

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest


@pytest.fixture(autouse=True)
def _offline_flags(monkeypatch):
    monkeypatch.setenv("PLUSONE_LLM", "0")
    monkeypatch.setenv("PLUSONE_IMAGINE", "0")
    monkeypatch.setenv("PLUSONE_TTS", "0")
    monkeypatch.setenv("LINQ_SKIP_VERIFY", "1")
