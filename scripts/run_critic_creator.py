"""scripts/run_critic_creator.py — Critic-Creator on one golden entry (W5 Lab Step 5).

Usage:
    python scripts/run_critic_creator.py --golden-id g015 \\
        --creator-model gpt-4o-mini --judge-model gpt-4o \\
        --max-rounds 3 --threshold 3.5 --output docs/critic-creator-trace.md
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.eval.critic_creator import critic_creator, render_trace, write_trace
from src.eval.golden import get_entry


async def run(args) -> int:
    entry = get_entry(args.golden_set, args.golden_id)
    system_prompt = Path(args.system_prompt).read_text(encoding="utf-8").strip()
    print(f"Running Critic-Creator on {args.golden_id}")
    print(f"  question      : {entry.question}")
    print(f"  creator model : {args.creator_model}")
    print(f"  judge model   : {args.judge_model} (also the blind critic)")
    print(f"  max rounds    : {args.max_rounds}")
    print(f"  convergence   : mean >= {args.threshold}\n")
    result = await critic_creator(entry.question, entry.ideal_answer, system_prompt=system_prompt,
                                  creator_model=args.creator_model, judge_model=args.judge_model,
                                  max_rounds=args.max_rounds, threshold=args.threshold)
    print(f"\nFinal answer:\n  {result['final_answer'][:400]}")
    print(f"\nTotal cost: ${result['total_cost_usd']:.6f}")
    write_trace(args.output, render_trace(args.golden_id, entry, result, creator_model=args.creator_model,
                                          judge_model=args.judge_model, max_rounds=args.max_rounds,
                                          threshold=args.threshold, system_prompt_file=args.system_prompt))
    print(f"Trace written to {args.output}")
    return 0


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="W5 Step 5: Critic-Creator loop on one golden entry")
    p.add_argument("--golden-id", required=True)
    p.add_argument("--golden-set", default="data/golden_set.jsonl")
    p.add_argument("--system-prompt", default="data/prompt-v1.txt", help="creator's system prompt")
    p.add_argument("--creator-model", default="gpt-4o-mini")
    p.add_argument("--judge-model", default="gpt-4o")
    p.add_argument("--max-rounds", type=int, default=3)
    p.add_argument("--threshold", type=float, default=3.5)
    p.add_argument("--output", default="docs/critic-creator-trace.md")
    return p.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))
