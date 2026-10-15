"""pipeline.py — Week 2 hands-on starter.

We'll fill in the TODOs together during the live session. The pieces:

    Step 2 — async def ask_llm                 (one call)
    Step 3 — ask_llm_with_retry                (exponential backoff)
    Step 4 — run_batch with asyncio.gather     (parallel fan-out)
    Step 5 — JSON-formatted structured logging

For the live demo we call ``fake_ask_llm`` from ``fake_llm.py`` —
no API quota, no network flakiness, and a ``fail_rate`` knob so retries
fire on demand. In the lab you'll swap to the real ``AsyncOpenAI`` client
(same ``Question``/``Answer`` shape — only one import changes).

Run it (after the TODOs are filled):
    python pipeline.py           # fail_rate = 0.0  (clean parallel run)
    python pipeline.py 0.4       # fail_rate = 0.4  (forces retries)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

# Live-session stand-in. Same Pydantic shape as the real call.
from .fake_llm import Question, Answer, fake_ask_llm, FakeLLMError


# ---------- Step 2: one async call ----------
async def ask_llm(q: Question, fail_rate: float = 0.0) -> Answer:
    """One call. Live demo: fake. Lab: real AsyncOpenAI (same signature)."""
    ans = await fake_ask_llm(q, fail_rate=fail_rate)
    log.info(f"asked: {q.text[:40]}")
    return ans


# ---------- Step 3: retry with exponential backoff ----------
async def ask_llm_with_retry(
    q: Question, tries: int = 3, fail_rate: float = 0.0
) -> Answer:
    """Retry up to ``tries`` times. Wait 1 s, 2 s, 4 s between attempts."""
    for attempt in range(tries):
        try:
            ans = await ask_llm(q, fail_rate=fail_rate)
            ans.retries = attempt              # 0 = succeeded first time
            return ans
        except Exception as exc:
            if attempt == tries - 1:           # last attempt — let the caller see it
                raise
            log.warning(f"retry {attempt + 1} for: {q.text[:40]} ({exc})")
            await asyncio.sleep(2 ** attempt)  # 1 s, then 2 s
    raise RuntimeError("unreachable")


# ---------- Step 4: gather it all together ----------
async def run_batch(
    questions: list[Question], fail_rate: float = 0.0
) -> list[Answer]:
    """Fire all questions in parallel via ``asyncio.gather``."""
    tasks = [ask_llm_with_retry(q, fail_rate=fail_rate) for q in questions]
    return await asyncio.gather(*tasks)


# ---------- W2 activity: stream answers as they finish ----------
async def run_batch_stream(
    questions: list[Question], fail_rate: float = 0.0
) -> list[Answer]:
    """Like run_batch, but prints each answer the moment it arrives.

    Returns answers in completion order, not input order.
    """
    tasks = [ask_llm_with_retry(q, fail_rate=fail_rate) for q in questions]
    results: list[Answer] = []
    for coro in asyncio.as_completed(tasks):
        ans = await coro
        print(f"  ✓ {ans.text[:60]}...")            # arrives the instant it's ready
        results.append(ans)
    return results


# ---------- Step 5: structured (JSON) logging ----------
class JsonFormatter(logging.Formatter):
    """One JSON record per log line: ts / level / msg."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "ts":    round(time.time(), 3),
            "level": record.levelname,
            "msg":   record.getMessage(),
        })


log = logging.getLogger("pipeline")
log.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter())
log.addHandler(_handler)


# ---------- main ----------
if __name__ == "__main__":
    import sys

    fail_rate = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    sample = [
        Question(text="What is RAG in one sentence?"),
        Question(text="Name three uses of vector databases."),
        Question(text="Why might an LLM hallucinate?"),
    ]
    started = time.time()
    answers = asyncio.run(run_batch(sample, fail_rate=fail_rate))
    elapsed = time.time() - started
    print(f"\n{len(answers)} answers in {elapsed:.2f}s\n")
    for a in answers:
        print(f"- {a.text[:80]}")
