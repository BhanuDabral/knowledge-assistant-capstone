"""Typed configuration and run summary — Pydantic v2.

Two models with different roles:
  - Settings:    config for a run (validated at construction, so a bad value
                 such as batch_size=0 fails here, not deep inside the pipeline)
  - RunSummary:  what one run did (one row per execution, built at the end)
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr


def _openai_key_from_env() -> SecretStr | None:
    """OPENAI_API_KEY from the environment or .env. SecretStr: prints as ********** in logs."""
    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    return SecretStr(key) if key else None


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

    # W4 — fields the W4 pipeline reads (missing from the course Settings, which
    # made its real-API path crash with AttributeError).
    openai_api_key:  SecretStr | None = Field(default_factory=_openai_key_from_env)
    max_retries:     int   = Field(2, ge=0, le=5)        # 2 retries = 3 attempts, as in W2
    retry_delay_s:   float = Field(1.0, ge=0.0)          # backoff 1 s, then 2 s
    answers_db:      Path  = Path("data/answers.db")     # W4 answers table (not the W2 results.db)
    max_input_tokens: int  = Field(2000, gt=0)           # tiktoken guard: longer questions -> 422, no LLM call


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
