"""scripts/run_pairwise.py — prompt v1 vs v2 on the golden set (W5 Lab Step 4b).

Written by Claude Code from the W5 lab guide's spec (the course bundle's
AI-RAG_W5_run_pairwise.py was not available).

Capstone choice: candidates are generated IN-PROCESS by the same ask_llm() that
/ask_batched calls, with Settings(system_prompt_file=...) set per version. This
avoids the guide's workaround (restart uvicorn once per prompt) and avoids adding
a caller-controlled system_prompt to the public API.

Usage:
    python scripts/run_pairwise.py \\
        --prompt-v1 data/prompt-v1.txt --prompt-v2 data/prompt-v2.txt \\
        --golden-set data/golden_set.jsonl --judge-model gpt-4o \\
        --output data/pairwise-001-results.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.eval.golden import load_golden
from src.eval.pairwise import pairwise_compare
from src.pipeline.llm import ask_llm
from src.pipeline.models import Question
from src.pipeline.settings import Settings


def as_text(answer) -> str:
    text = answer.content
    if answer.sources:
        text += "\n\nSources given: " + "; ".join(answer.sources)
    return text


async def one(entry, s1: Settings, s2: Settings, judge_model: str) -> dict:
    q = Question(question=entry.question)
    a1, a2 = await asyncio.gather(ask_llm(q, s1), ask_llm(q, s2))
    v = await pairwise_compare(entry.question, entry.ideal_answer, as_text(a1), as_text(a2), model=judge_model)
    return {"id": entry.id, "bucket": entry.bucket, "question": entry.question,
            "answer_v1": as_text(a1), "answer_v2": as_text(a2), **v,
            "candidate_cost_usd": a1.cost_usd + a2.cost_usd}


async def run(args) -> int:
    entries = load_golden(args.golden_set)
    s1 = Settings(model=args.candidate_model, system_prompt_file=Path(args.prompt_v1))
    s2 = Settings(model=args.candidate_model, system_prompt_file=Path(args.prompt_v2))
    print(f"Pairwise on {len(entries)} entries · candidate {args.candidate_model} · judge {args.judge_model}")
    print(f"  v1 = {args.prompt_v1}   v2 = {args.prompt_v2}   (each pair judged in BOTH orders)\n")

    start = time.perf_counter()
    sem = asyncio.Semaphore(args.concurrency)

    async def guarded(e):
        async with sem:
            r = await one(e, s1, s2, args.judge_model)
            print(f"  {r['id']} [{r['bucket']:6}] {r['result']:9}  (v1-first: {r['forward']['winner']}, "
                  f"v2-first: {r['reverse']['winner']})")
            return r

    rows = await asyncio.gather(*(guarded(e) for e in entries))
    elapsed = time.perf_counter() - start

    c = Counter(r["result"] for r in rows)
    n = len(rows)
    judge_cost = sum(r["cost_usd"] for r in rows)
    cand_cost = sum(r["candidate_cost_usd"] for r in rows)
    Path(args.output).write_text(json.dumps({
        "prompt_v1": Path(args.prompt_v1).read_text(), "prompt_v2": Path(args.prompt_v2).read_text(),
        "candidate_model": args.candidate_model, "judge_model": args.judge_model,
        "summary": dict(c), "candidate_cost_usd": cand_cost, "judge_cost_usd": judge_cost,
        "results": rows}, indent=1, ensure_ascii=False), encoding="utf-8")

    print()
    print("=" * 60)
    print("Pairwise summary")
    print("-" * 60)
    print(f"  v1 wins      : {c['v1']}")
    print(f"  v2 wins      : {c['v2']}")
    print(f"  tie          : {c['tie']}")
    print(f"  ambiguous    : {c['ambiguous']}  (forward/reverse disagreed — position bias on these)")
    print(f"  position-bias rate : {c['ambiguous']}/{n}  =  {100 * c['ambiguous'] / n:.0f}%")
    print(f"  cost (candidates + judge) : ${cand_cost:.6f} + ${judge_cost:.6f}")
    print(f"  wall-clock   : {elapsed:.1f}s")
    print(f"\nPer-question results saved to {args.output}")
    return 0


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="W5 Step 4: pairwise prompt comparison")
    p.add_argument("--prompt-v1", default="data/prompt-v1.txt")
    p.add_argument("--prompt-v2", default="data/prompt-v2.txt")
    p.add_argument("--golden-set", default="data/golden_set.jsonl")
    p.add_argument("--candidate-model", default="gpt-4o-mini")
    p.add_argument("--judge-model", default="gpt-4o")
    p.add_argument("--output", default="data/pairwise-001-results.json")
    p.add_argument("--concurrency", type=int, default=4)
    return p.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))
