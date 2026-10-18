"""scripts/run_eval.py — judge the app's answers on the golden set (W5 Lab Step 3b).

Written by Claude Code from the W5 lab guide's spec (the course bundle's
AI-RAG_W5_run_eval.py was not available).

For each golden entry: POST the question to the running API's /ask_batched
(the real app path), score the answer with judge_one() against the ideal
answer, and save the verdict to the eval_runs table under --label.

Usage (API running in another terminal: uvicorn api.main:app --port 8000):
    python scripts/run_eval.py \\
        --golden-set data/golden_set.jsonl --db data/answers.db \\
        --api-url http://localhost:8000 --judge-model gpt-4o --label eval-run-001
"""
from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.eval.golden import load_golden
from src.eval.judge import judge_one
from src.pipeline.answer_store import connect, eval_run_summary, save_eval_run
from src.pipeline.settings import Settings


def candidate_text(answer: dict) -> str:
    """What the judge sees: the answer, plus any sources the model claimed (so invented ones count)."""
    text = answer["content"]
    if answer.get("sources"):
        text += "\n\nSources given: " + "; ".join(answer["sources"])
    return text


async def run(args) -> int:
    entries = load_golden(args.golden_set)
    with connect(args.db) as conn:                         # creates eval_runs if needed
        if conn.execute("SELECT COUNT(*) FROM eval_runs WHERE eval_run_label = ?",
                        (args.label,)).fetchone()[0]:
            print(f"label {args.label!r} already has rows in {args.db}; pick a new --label")
            return 1

    print(f"Judging {len(entries)} golden entries · candidate via {args.api_url}/ask_batched "
          f"({args.candidate_model}) · judge {args.judge_model} · label {args.label}\n")
    start = time.perf_counter()
    async with httpx.AsyncClient(base_url=args.api_url, timeout=120) as http:
        for e in entries:
            r = await http.post("/ask_batched", json={"question": e.question})
            r.raise_for_status()
            answer = r.json()
            cand = candidate_text(answer)
            score = await judge_one(e.question, e.ideal_answer, cand, model=args.judge_model)
            with connect(args.db) as conn:                 # one commit per entry: a crash keeps progress
                save_eval_run(
                    conn, golden_id=e.id, question=e.question, candidate_answer=cand,
                    ideal_answer=e.ideal_answer, candidate_model=args.candidate_model,
                    judge_model=args.judge_model, accuracy=score.accuracy,
                    groundedness=score.groundedness, format=score.format,
                    reasoning=score.reasoning, eval_run_label=args.label,
                    candidate_cost_usd=answer.get("cost_usd", 0.0), judge_cost_usd=score.cost_usd,
                )
            print(f"  {e.id} [{e.bucket:6}] a={score.accuracy} g={score.groundedness} f={score.format}"
                  f"  ·  {e.question[:60]}")
    elapsed = time.perf_counter() - start

    with sqlite3.connect(args.db) as conn:
        s = eval_run_summary(conn, args.label)
    d = s["accuracy_dist"]
    print()
    print("=" * 60)
    print(f"Aggregate for label={args.label!r}")
    print("-" * 60)
    print(f"  n entries scored   : {s['n']}")
    print(f"  avg accuracy       : {s['avg_accuracy']:.2f}")
    print(f"  avg groundedness   : {s['avg_groundedness']:.2f}")
    print(f"  avg format         : {s['avg_format']:.2f}")
    print(f"  accuracy 4 / 3 / 2 / 1 : {d[4]} / {d[3]} / {d[2]} / {d[1]}")
    print(f"  cost (candidate + judge) : ${s['candidate_cost_usd']:.6f} + ${s['judge_cost_usd']:.6f}")
    print(f"  wall-clock         : {elapsed:.1f}s")
    print("\nWrite the 1-page summary in docs/eval-run-001.md — your M1 eval baseline.")
    return 0


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="W5 Step 3: LLM-as-judge over the golden set")
    p.add_argument("--golden-set", default="data/golden_set.jsonl")
    p.add_argument("--db", default="data/answers.db")
    p.add_argument("--api-url", default="http://localhost:8000")
    p.add_argument("--judge-model", default="gpt-4o")
    p.add_argument("--candidate-model", default=Settings().model,
                   help="label only: the model the running API uses (default: Settings().model)")
    p.add_argument("--label", default="eval-run-001")
    return p.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))
