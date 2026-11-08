"""scripts/stress_test.py — concurrent stress test for /ask, with raw results kept.

Sends N parallel POST requests through your FastAPI service and reports
timing + any errors. Used in W3 Lab Step 3 sub-step 3d; the source of KPI 3 (p95 latency).

DR #1 feedback ("retain raw latency results and configuration"): every run now
writes one JSON file with the configuration, every request's raw timing and the
summary, so the p95 in the ADR can be traced and re-computed. Questions come from
the golden set (the capstone's real questions), not the course's HR placeholders.

p95 is nearest-rank: the ceil(0.95 * n)-th fastest request. With n = 10 that is
simply the slowest request, so use --requests 40 or more for a meaningful p95.

Usage (API running in another terminal: uvicorn api.main:app --port 8000):
    python scripts/stress_test.py --requests 40 --concurrent 3
    python scripts/stress_test.py --requests 40 --concurrent 3 --output docs/runs/latency/my-run.json
"""
import argparse
import asyncio
import json
import math
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_questions(path: Path) -> list[str]:
    """Questions from a golden-set JSONL file (one {"question": ...} object per line)."""
    questions = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            questions.append(json.loads(line)["question"])
    if not questions:
        raise ValueError(f"no questions in {path}")
    return questions


def nearest_rank(sorted_values: list[float], pct: float) -> float:
    """Nearest-rank percentile of an ascending list: the ceil(pct/100 * n)-th value."""
    if not sorted_values:
        raise ValueError("no values")
    rank = max(1, math.ceil(pct / 100 * len(sorted_values)))
    return sorted_values[rank - 1]


def summarise(results: list[dict], total_s: float) -> dict:
    """Counts, throughput and min / p50 / p95 / max latency over the successful requests."""
    ok = sorted(r["elapsed_s"] for r in results if r["status"] == 200)
    summary = {"requests": len(results), "successes": len(ok), "failures": len(results) - len(ok),
               "wall_time_s": round(total_s, 2), "req_per_s": round(len(results) / total_s, 2) if total_s else None}
    if ok:
        summary.update({"min_s": round(ok[0], 2), "p50_s": round(nearest_rank(ok, 50), 2),
                        "p95_s": round(nearest_rank(ok, 95), 2), "max_s": round(ok[-1], 2)})
    return summary


def run_config(args: argparse.Namespace, n_questions: int) -> dict:
    """What produced these numbers: client arguments, server settings as read from the local .env, git commit."""
    from src.pipeline.settings import Settings
    settings = Settings()
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "src", "api"], cwd=ROOT,
                                    capture_output=True, text=True).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    return {
        "endpoint": f"{args.api_url}/ask",
        "requests": args.requests,
        "concurrent": args.concurrent,
        "timeout_s": args.timeout,
        "questions_file": str(args.questions),
        "n_distinct_questions": n_questions,
        # Read from this machine's .env: start uvicorn from the same repo and .env so they match the server.
        "server_model": settings.model,
        "server_system_prompt_file": str(settings.system_prompt_file) if settings.system_prompt_file else None,
        "server_use_fake": settings.use_fake,
        "git_commit": commit,
        "src_or_api_uncommitted_changes": dirty,
        "python": platform.python_version(),
        "platform": platform.platform(),
    }


async def ask_one(client: httpx.AsyncClient, url: str, question: str, idx: int, timeout: float) -> dict:
    start = time.perf_counter()
    try:
        response = await client.post(url, json={"question": question}, timeout=timeout)
        body = await response.aread()
        return {"idx": idx, "question": question, "status": response.status_code,
                "elapsed_s": round(time.perf_counter() - start, 3), "bytes": len(body)}
    except Exception as e:
        return {"idx": idx, "question": question, "status": "ERR", "error": f"{type(e).__name__}: {e}",
                "elapsed_s": round(time.perf_counter() - start, 3)}


async def run(args: argparse.Namespace) -> dict:
    questions = load_questions(Path(args.questions))
    sem = asyncio.Semaphore(args.concurrent)
    url = f"{args.api_url}/ask"

    async def bounded(client, q, i):
        async with sem:
            return await ask_one(client, url, q, i, args.timeout)

    print(f"Stress test: {args.requests} requests, up to {args.concurrent} concurrent, "
          f"{len(questions)} golden-set questions")
    print("─" * 60)
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    async with httpx.AsyncClient() as client:
        tasks = [bounded(client, questions[i % len(questions)], i) for i in range(args.requests)]
        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        total = time.perf_counter() - start

    report = {"started_at_utc": started_at, "config": run_config(args, len(questions)),
              "summary": summarise(results, total), "requests": results}
    s = report["summary"]
    print(f"Total wall time:   {s['wall_time_s']:.2f}s")
    print(f"Successes:         {s['successes']} / {s['requests']}")
    print(f"Effective req/s:   {s['req_per_s']:.2f}")
    if s["successes"]:
        print("\nLatency (successful requests, nearest-rank):")
        for k in ("min_s", "p50_s", "p95_s", "max_s"):
            print(f"  {k[:-2] + ':':6} {s[k]:.2f}s")
    failures = [r for r in results if r["status"] != 200]
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for f in failures[:5]:
            print(f"  idx={f['idx']}  {f.get('error', f.get('status'))}")

    out = Path(args.output) if args.output else ROOT / "docs/runs/latency" / f"stress-{started_at.replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nRaw results + config saved to {out}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrent", type=int, default=10)
    parser.add_argument("--questions", default=str(ROOT / "data/golden_set.jsonl"))
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--output", default=None, help="JSON file (default: docs/runs/latency/stress-<utc>.json)")
    asyncio.run(run(parser.parse_args()))
