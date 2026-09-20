"""Load repo-root .env and accept LINQ as an alias for LINQ_API_KEY."""

from __future__ import annotations

import os
from pathlib import Path


def load_plusone_env() -> None:
    root = Path(__file__).resolve().parents[1]
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None
    if load_dotenv is not None:
        load_dotenv(root / ".env")
        load_dotenv(root / "env")
        load_dotenv(Path(__file__).resolve().parent / ".env")
    if os.getenv("LINQ") and not os.getenv("LINQ_API_KEY"):
        os.environ["LINQ_API_KEY"] = os.environ["LINQ"]


def linq_api_key() -> str:
    return os.environ.get("LINQ_API_KEY") or os.environ.get("LINQ") or ""
