"""Typed runtime configuration — Pydantic v2.

Settings holds the config for a run. It is validated when it is constructed,
so a bad value (e.g. batch_size=0) fails here with a clear error instead of
deep inside the pipeline.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime configuration. Validated at construction."""

    questions_csv: Path  = Path("data/questions.csv")
    results_json:  Path  = Path("results.json")
    results_db:    Path  = Path("results.db")
    batch_size:    int   = Field(5,   gt=0, le=20)      # 0 < batch_size <= 20
    fail_rate:     float = Field(0.0, ge=0.0, le=1.0)   # 0.0 <= fail_rate <= 1.0
    model:         str   = "gpt-4o-mini"
    use_fake:      bool  = True
