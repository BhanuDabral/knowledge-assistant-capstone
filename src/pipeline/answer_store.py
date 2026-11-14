"""src/pipeline/answer_store.py — W4 answers store (course reference store.py).

Renamed so it does not replace the W2 store.py (runs + answers in results.db),
which the W2 batch pipeline still uses. Default database: data/answers.db.

Extends the W2 SQLite store with two new columns:
  • cost_usd  REAL    — actual per-call cost from response.usage × rates
  • model     TEXT    — which model produced the answer

Adds ensure_schema() that runs idempotent ALTER TABLE migrations so a cohort
member can rerun without breaking an existing answers.db.

W5: adds the `eval_runs` table (one row per golden entry × judge run), created
by the same ensure_schema(). The W4 `answers` table is unchanged. The lab guide
puts this in store.py; here it lives with the other answers.db tables.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


# ─── Schema (idempotent) ────────────────────────────────────────────────────
_BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS answers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    question        TEXT NOT NULL,
    content         TEXT NOT NULL,
    retries         INTEGER DEFAULT 0,
    cost_usd        REAL DEFAULT 0.0,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

# Columns added in W4. Each entry: (column_name, column_def).
# Applied via ALTER TABLE only if missing — so the migration is safe to rerun.
_W4_NEW_COLUMNS = [
    ("model",          "TEXT"),
    ("confidence",     "REAL"),
    ("sources_json",   "TEXT"),  # list[str] stored as JSON
    ("schema_version", "TEXT DEFAULT 'v1'"),
]

# W5 — judge verdicts. Columns as in the lab guide (Step 0b), plus two cost
# columns so the eval run can be checked against the ADR cost budget.
_EVAL_RUNS_SCHEMA = """
CREATE TABLE IF NOT EXISTS eval_runs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    golden_id          TEXT NOT NULL,
    question           TEXT NOT NULL,
    candidate_answer   TEXT NOT NULL,
    ideal_answer       TEXT NOT NULL,
    candidate_model    TEXT NOT NULL,
    judge_model        TEXT NOT NULL,
    accuracy           INTEGER NOT NULL,
    groundedness       INTEGER NOT NULL,
    format             INTEGER NOT NULL,
    reasoning          TEXT NOT NULL,
    eval_run_label     TEXT DEFAULT 'eval-run-001',
    created_at         TEXT DEFAULT CURRENT_TIMESTAMP,
    candidate_cost_usd REAL DEFAULT 0.0,
    judge_cost_usd     REAL DEFAULT 0.0
);
"""


# W6 — one row per golden entry × RAG eval run: what was retrieved, cited and measured.
# Judge verdicts (accuracy etc.) stay in eval_runs under the same label.
_RAG_RUNS_SCHEMA = """
CREATE TABLE IF NOT EXISTS rag_runs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    label              TEXT NOT NULL,
    golden_id          TEXT NOT NULL,
    condition          TEXT NOT NULL,          -- rag | none | oracle
    index_name         TEXT,                   -- e.g. data/index/medium (rag only)
    chunk_size         INTEGER,
    chunk_overlap      INTEGER,
    k                  INTEGER,
    question           TEXT NOT NULL,
    answer             TEXT NOT NULL,
    cited_json         TEXT,                   -- chunk ids the model cited (filtered to retrieved)
    retrieved_json     TEXT,                   -- [{chunk_id, source, page_start, page_end, score}]
    hit_doc            INTEGER,                -- 1/0; NULL when out of scope or no retrieval
    hit_page           INTEGER,
    declined           INTEGER,                -- 1/0 (refusal classifier)
    support            TEXT,                   -- full | partial | none; NULL if no context or declined
    support_json       TEXT,
    latency_s          REAL,
    candidate_cost_usd REAL DEFAULT 0.0,       -- chat + query embedding
    eval_cost_usd      REAL DEFAULT 0.0,       -- refusal + citation judges (accuracy judge is in eval_runs)
    created_at         TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


_RAG_RUNS_COLUMNS = {line.split()[0] for line in _RAG_RUNS_SCHEMA.splitlines()
                     if line.startswith("    ") and not line.strip().startswith(("--", ")"))} - {"id"}


def ensure_schema(db_path: str | Path) -> None:
    """Create answers table if missing, then add any missing W4 columns.

    Safe to call on an empty file, on a W2/W3 db, or on a fully-migrated db.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(_BASE_SCHEMA)
        # Read current columns.
        cur = conn.execute("PRAGMA table_info(answers)")
        existing = {row[1] for row in cur.fetchall()}
        for col_name, col_def in _W4_NEW_COLUMNS:
            if col_name not in existing:
                conn.execute(f"ALTER TABLE answers ADD COLUMN {col_name} {col_def}")
        conn.executescript(_EVAL_RUNS_SCHEMA)                # W5; no-op if it exists
        conn.executescript(_RAG_RUNS_SCHEMA)                 # W6; no-op if it exists
        conn.commit()
    finally:
        conn.close()


@contextmanager
def connect(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    """Open a connection with the W4 schema guaranteed in place."""
    ensure_schema(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_answer(
    conn: sqlite3.Connection,
    *,
    question: str,
    content: str,
    retries: int,
    cost_usd: float,
    model: str,
    confidence: float,
    sources: list[str],
    schema_version: str = "v1",
) -> int:
    """Insert one row and return its rowid."""
    cur = conn.execute(
        """
        INSERT INTO answers (
            question, content, retries, cost_usd, model,
            confidence, sources_json, schema_version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            question, content, retries, cost_usd, model,
            confidence, json.dumps(sources), schema_version,
        ),
    )
    return cur.lastrowid


def save_eval_run(
    conn: sqlite3.Connection,
    *,
    golden_id: str,
    question: str,
    candidate_answer: str,
    ideal_answer: str,
    candidate_model: str,
    judge_model: str,
    accuracy: int,
    groundedness: int,
    format: int,
    reasoning: str,
    eval_run_label: str,
    candidate_cost_usd: float = 0.0,
    judge_cost_usd: float = 0.0,
) -> int:
    """Insert one judge verdict into eval_runs and return its rowid."""
    cur = conn.execute(
        """
        INSERT INTO eval_runs (
            golden_id, question, candidate_answer, ideal_answer, candidate_model,
            judge_model, accuracy, groundedness, format, reasoning, eval_run_label,
            candidate_cost_usd, judge_cost_usd
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            golden_id, question, candidate_answer, ideal_answer, candidate_model,
            judge_model, accuracy, groundedness, format, reasoning, eval_run_label,
            candidate_cost_usd, judge_cost_usd,
        ),
    )
    return cur.lastrowid


def save_rag_run(conn: sqlite3.Connection, **row) -> int:
    """Insert one rag_runs row (keyword arguments = column names) and return its rowid."""
    for key in ("cited", "retrieved", "support_detail"):
        if key in row:
            row[{"cited": "cited_json", "retrieved": "retrieved_json",
                 "support_detail": "support_json"}[key]] = json.dumps(row.pop(key))
    unknown = set(row) - _RAG_RUNS_COLUMNS
    if unknown:
        raise ValueError(f"not rag_runs columns: {sorted(unknown)}")
    cols = ", ".join(row)
    cur = conn.execute(f"INSERT INTO rag_runs ({cols}) VALUES ({', '.join('?' for _ in row)})",
                       tuple(row.values()))
    return cur.lastrowid


def eval_run_summary(conn: sqlite3.Connection, label: str) -> dict:
    """Aggregate one eval run: n, averages, accuracy distribution, total cost."""
    n, acc, grd, fmt, cand_cost, judge_cost = conn.execute(
        """
        SELECT COUNT(*), AVG(accuracy), AVG(groundedness), AVG(format),
               COALESCE(SUM(candidate_cost_usd), 0), COALESCE(SUM(judge_cost_usd), 0)
        FROM eval_runs WHERE eval_run_label = ?
        """,
        (label,),
    ).fetchone()
    dist = dict(conn.execute(
        "SELECT accuracy, COUNT(*) FROM eval_runs WHERE eval_run_label = ? GROUP BY accuracy",
        (label,),
    ).fetchall())
    return {
        "label": label, "n": n,
        "avg_accuracy": acc, "avg_groundedness": grd, "avg_format": fmt,
        "accuracy_dist": {k: dist.get(k, 0) for k in (4, 3, 2, 1)},
        "candidate_cost_usd": cand_cost, "judge_cost_usd": judge_cost,
    }


def query_results(conn: sqlite3.Connection, model: str | None = None) -> list[dict]:
    """Read back rows, optionally filtered by model. Useful in Step 3."""
    if model is None:
        cur = conn.execute("SELECT * FROM answers ORDER BY id")
    else:
        cur = conn.execute("SELECT * FROM answers WHERE model = ? ORDER BY id", (model,))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
