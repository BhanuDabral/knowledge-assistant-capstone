"""pipeline.py — Week 2 async batch pipeline.

The pieces:

    ask_llm              one call (fake or real LLM)
    ask_llm_with_retry   retry with exponential backoff (1 s, 2 s)
    run_batch            every question in parallel via asyncio.gather
    run_batch_stream     W2 activity: answers in completion order (as_completed)

Configuration comes from the typed ``Settings`` model; logs are JSON lines
written to logs/pipeline.log.

Run it from the repo root:
    python -m src.pipeline.pipeline
"""
from __future__ import annotations

import asyncio
import csv
import json
import time
from pathlib import Path

from .logging_config import get_logger
from .settings import Settings, RunSummary

log = get_logger()


# ---------- LLM client: fake or real, chosen once at import ----------
_settings_for_import = Settings()

if _settings_for_import.use_fake:
    # Stand-in with the same Pydantic shape as the real call.
    from .fake_llm import Question, Answer, fake_ask_llm, FakeLLMError
else:
    from dotenv import load_dotenv
    from openai import AsyncOpenAI
    from pydantic import BaseModel

    load_dotenv()                      # OPENAI_API_KEY from .env
    _client = AsyncOpenAI()

    class Question(BaseModel):
        text: str

    class Answer(BaseModel):
        question: str
        text:     str
        cost_usd: float
        retries:  int = 0


# ---------- CSV loader ----------
def load_questions(path: str | Path = "data/questions.csv") -> list[Question]:
    """Read questions from a CSV with a ``text`` column; blank rows are skipped."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [Question(text=row["text"]) for row in rows if row.get("text")]


# ---------- Step 2: one async call ----------
async def ask_llm(q: Question, fail_rate: float = 0.0) -> Answer:
    """One call — fake or real AsyncOpenAI, depending on Settings.use_fake."""
    if _settings_for_import.use_fake:
        ans = await fake_ask_llm(q, fail_rate=fail_rate)
    else:
        resp = await _client.chat.completions.create(
            model=_settings_for_import.model,
            messages=[{"role": "user", "content": q.text}],
        )
        ans = Answer(
            question=q.text,
            text=resp.choices[0].message.content,
            cost_usd=0.0001,                   # placeholder; real cost from usage comes later
        )
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


async def run_in_batches(
    questions: list[Question],
    batch_size: int = 5,
    fail_rate: float = 0.0,
) -> list[Answer]:
    """Gather in chunks of ``batch_size``, with a 100 ms pause between chunks."""
    out: list[Answer] = []
    for i in range(0, len(questions), batch_size):
        chunk = questions[i : i + batch_size]
        log.info(f"batch {i // batch_size + 1}: {len(chunk)} questions")
        batch_answers = await asyncio.gather(
            *(ask_llm_with_retry(q, fail_rate=fail_rate) for q in chunk)
        )
        out.extend(batch_answers)
        await asyncio.sleep(0.1)               # gentle pace between batches
    return out


# ---------- Run summary ----------
def summarise_run(
    answers: list[Answer],
    *,
    started_at: float,
    elapsed: float,
    fail_rate: float,
    use_fake: bool,
) -> RunSummary:
    """Roll a list of Answers plus wall-clock data into one RunSummary."""
    return RunSummary(
        started_at      = started_at,
        elapsed_seconds = elapsed,
        n_questions     = len(answers),
        n_succeeded     = len(answers),
        n_retries_total = sum(a.retries for a in answers),
        total_cost_usd  = sum(a.cost_usd for a in answers),
        fail_rate       = fail_rate,
        use_fake        = use_fake,
    )


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


# ---------- main ----------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the W2 async batch pipeline.")
    parser.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="process only the first N questions from the CSV (N >= 1)",
    )
    parser.add_argument(
        "--questions", type=Path, default=None, metavar="PATH",
        help="read questions from this CSV instead of Settings.questions_csv",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be 1 or more")
    if args.questions is not None and not args.questions.is_file():
        parser.error(f"--questions: no such file: {args.questions}")

    settings = Settings()
    if args.questions is not None:
        settings.questions_csv = args.questions
    log.info(f"config: {settings.model_dump(mode='json')}")

    questions = load_questions(settings.questions_csv)
    log.info(f"loaded {len(questions)} questions")
    if args.limit is not None:
        questions = questions[: args.limit]
        log.info(f"--limit {args.limit}: running the first {len(questions)} questions")

    started = time.time()
    answers = asyncio.run(
        run_in_batches(
            questions,
            batch_size=settings.batch_size,
            fail_rate=settings.fail_rate,
        )
    )
    elapsed = time.time() - started
    log.info(f"done: {len(answers)} answers in {elapsed:.2f}s")

    summary = summarise_run(
        answers,
        started_at = started,
        elapsed    = elapsed,
        fail_rate  = settings.fail_rate,
        use_fake   = settings.use_fake,
    )
    log.info(f"summary: {summary.model_dump_json()}")

    # The run as one structured artefact: summary + every answer
    settings.results_json.write_text(
        json.dumps({
            "summary": summary.model_dump(mode="json"),
            "answers": [a.model_dump() for a in answers],
        }, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(answers)} answers to {settings.results_json} in {elapsed:.2f}s")

    # SQLite persistence. Imported here, not at the top: store.py imports
    # Answer from this module, so a top-level import would be circular.
    from .store import connect, write_run, write_answers
    with connect(settings.results_db) as con:
        run_id = write_run(con, summary)
        n      = write_answers(con, run_id, answers)
    log.info(f"persisted run {run_id} with {n} answers to {settings.results_db}")
