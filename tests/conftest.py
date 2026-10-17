"""tests/conftest.py — make the project root importable for tests.

Adds the repo root (the directory containing this `tests/` folder's parent)
to `sys.path` so tests can do `from src.pipeline.pipeline import ...` and
`from api.main import app` from anywhere.

Capstone addition: the W3 tests mock the fake-LLM path, so force fake mode
before any test imports the pipeline. Unit tests never call the real API.
"""
import os
import sys
from pathlib import Path

os.environ["PIPELINE_USE_FAKE"] = "1"

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
