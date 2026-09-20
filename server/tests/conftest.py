import os
import sys
from pathlib import Path

os.environ.setdefault("PLUSONE_LLM", "0")
os.environ.setdefault("PLUSONE_IMAGINE", "0")
os.environ.setdefault("PLUSONE_TTS", "0")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
