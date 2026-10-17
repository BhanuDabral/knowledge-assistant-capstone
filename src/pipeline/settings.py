"""Typed configuration and run summary — Pydantic v2.

Two models with different roles:
  - Settings:    config for a run (validated at construction, so a bad value
                 such as batch_size=0 fails here, not deep inside the pipeline)
  - RunSummary:  what one run did (one row per execution, built at the end)
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


def _use_fake_from_env() -> bool:
    """PIPELINE_USE_FAKE=1/true/yes switches to the fake LLM (tests set it); default: real API."""
    return os.getenv("PIPELINE_USE_FAKE", "false").strip().lower() in {"1", "true", "yes"}


class Settings(BaseModel):
    """Runtime configuration. Validated at construction."""

    questions_csv: Path  = Path("data/questions.csv")
    results_json:  Path  = Path("results.json")
    results_db:    Path  = Path("results.db")
    batch_size:    int   = Field(5,   gt=0, le=20)      # 0 < batch_size <= 20
    fail_rate:     float = Field(0.0, ge=0.0, le=1.0)   # 0.0 <= fail_rate <= 1.0
    model:         str   = "gpt-4o-mini"
    use_fake:      bool  = Field(default_factory=_use_fake_from_env)


class RunSummary(BaseModel):
    """One row per pipeline execution. Persisted to the ``runs`` table."""

    started_at:       float                              # time.time() at run start
    elapsed_seconds:  float = Field(ge=0.0)
    n_questions:      int   = Field(ge=0)
    n_succeeded:      int   = Field(ge=0)
    n_retries_total:  int   = Field(ge=0)
    total_cost_usd:   float = Field(ge=0.0)
    fail_rate:        float = Field(ge=0.0, le=1.0)
    use_fake:         bool
