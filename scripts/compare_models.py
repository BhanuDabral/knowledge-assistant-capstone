"""W4 — scripts/compare_models.py

Lab Step 3 — run the same questions through two OpenAI models and persist
both result sets to SQLite (the W4 store has a `model` column for this).

Usage:
    # Defaults: gpt-4o-mini vs gpt-4o, the 10 W4 lab questions (data/w4_questions.csv)
    python scripts/compare_models.py

    # Override:
    python scripts/compare_models.py \\
        --models gpt-4o-mini,gpt-4o \\
        --questions data/questions.csv \\
        --db data/answers.db

After the run, inspect the persisted rows with:
    sqlite3 data/answers.db "SELECT model, COUNT(*), ROUND(SUM(cost_usd), 6) FROM answers GROUP BY model;"
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import sys
import time
from pathlib import Path

# Make the `src` package reachable when invoked as `python scripts/X.py`.
# Without this, Python's sys.path[0] is `scripts/` (the script's directory),
# not the project root, so `from src.pipeline...` raises ModuleNotFoundError.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline.models import Question
from src.pipeline.llm import ask_llm                          # capstone: W4 LLM layer in llm.py
from src.pipeline.settings import Settings
from src.pipeline.answer_store import connect, save_answer   # capstone: W4 store in answer_store.py


async def run_one_model(questions: list[str], model: str, db_path: Path) -> dict:
    """Run all questions through one model. Returns aggregate stats."""
    settings = Settings(model=model)
    # Real API unless PIPELINE_USE_FAKE=1. The course Settings defaulted use_fake=True,
    # which silently compared two fake runs; label fake rows so that can't happen unseen.
    label = "fake" if settings.use_fake else model
    if settings.use_fake:
        print(f"    WARNING: PIPELINE_USE_FAKE is set; {model} answers come from the fake LLM")
    start = time.perf_counter()
    total_cost = 0.0
    total_retries = 0

    with connect(db_path) as conn:
        for q in questions:
            answer = await ask_llm(Question(question=q), settings)
            total_cost += answer.cost_usd
            total_retries += answer.retries
            save_answer(
                conn,
                question=q,
                content=answer.content,
                retries=answer.retries,
                cost_usd=answer.cost_usd,
                model=label,
                confidence=answer.confidence,
                sources=answer.sources,
                schema_version=answer.schema_version,
            )

    elapsed = time.perf_counter() - start
    return {
        "model": label,
        "n": len(questions),
        "total_cost_usd": round(total_cost, 6),
        "total_retries": total_retries,
        "elapsed_s": round(elapsed, 2),
        "avg_cost_usd": round(total_cost / len(questions), 6),
    }


def load_questions(path: Path) -> list[str]:
    """Read questions from a CSV with a `question` or `text` header column.

    Capstone fix: the course version took column 0 and skipped the header only
    if it started with "question", so a `text` header (W2 / capstone CSVs) was
    asked as a question. Extra columns (e.g. source_document) are ignored.
    """
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        col = next((c for c in ("question", "text") if c in (reader.fieldnames or [])), None)
        if col is None:
            raise SystemExit(f"{path}: needs a 'question' or 'text' header column")
        return [row[col].strip() for row in reader if (row.get(col) or "").strip()]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run two-model comparison for W4 Lab Step 3")
    p.add_argument("--models", default="gpt-4o-mini,gpt-4o",
                   help="Comma-separated model ids (default: gpt-4o-mini,gpt-4o)")
    p.add_argument("--questions", default="data/w4_questions.csv",
                   help="Path to questions CSV (default: data/w4_questions.csv)")
    p.add_argument("--db", default="data/answers.db",
                   help="Path to SQLite db (default: data/answers.db)")
    return p.parse_args(argv)


async def main_async(args: argparse.Namespace) -> int:
    questions = load_questions(Path(args.questions))
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    print(f"Running {len(questions)} questions through: {', '.join(models)}")
    print(f"Persisting to: {db_path}")
    print()

    summaries = []
    for m in models:
        print(f"  → {m} …")
        summary = await run_one_model(questions, m, db_path)
        summaries.append(summary)
        print(
            f"    done — n={summary['n']}  "
            f"cost=${summary['total_cost_usd']}  "
            f"avg=${summary['avg_cost_usd']}/q  "
            f"retries={summary['total_retries']}  "
            f"time={summary['elapsed_s']}s"
        )

    print()
    print("=" * 60)
    print(f"{'Model':<20}  {'n':>4}  {'Total $':>10}  {'Avg $/q':>10}  {'Time':>8}")
    print("-" * 60)
    for s in summaries:
        print(
            f"{s['model']:<20}  {s['n']:>4}  "
            f"{s['total_cost_usd']:>10.6f}  "
            f"{s['avg_cost_usd']:>10.6f}  "
            f"{s['elapsed_s']:>7.2f}s"
        )
    if len(summaries) == 2:
        a, b = summaries
        ratio = b["total_cost_usd"] / a["total_cost_usd"] if a["total_cost_usd"] else 0
        print()
        print(f"  → {b['model']} cost {ratio:.1f}× more than {a['model']} on the same questions.")
    return 0


def main() -> int:
    args = parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
