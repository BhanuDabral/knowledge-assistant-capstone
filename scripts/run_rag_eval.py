"""scripts/run_rag_eval.py — the golden set through one condition, with the W6 + DR #1 measures.

Conditions (DR #1: compare retrieval with two controls, under one eval):
  rag     retrieve top-K from --index, answer from the passages      (the W6 system, /ask_batched)
  rag-stream  the same retrieval, answered the way /ask streams it    (what the Streamlit UI shows)
  none    no retrieval: the model alone, as in eval-run-003          (repeat it to see the noise)
  oracle  the golden entry's cited pages handed over as passages     (perfect retrieval: the ceiling)

All three use the same functions as the API (rag_answer / ask_llm), prompt v2,
gpt-4o-mini, in-process, one question at a time so latency is per question.

Per entry it records, in rag_runs: retrieved + cited chunks, document/page hit,
declined (refusal classifier), citation support (passages vs answer), latency
and cost. With --judge (default) the W5 judge (rubric v2) also scores accuracy
into eval_runs under the same label.

Usage:
    python scripts/run_rag_eval.py --label wk6-rag-medium --condition rag --index data/index/medium
    python scripts/run_rag_eval.py --label wk6-rag-small  --condition rag --index data/index/small --no-judge --no-support
    python scripts/run_rag_eval.py --label wk6-rag-medium-stream --condition rag-stream --index data/index/medium
    python scripts/run_rag_eval.py --label wk6-norag-r2   --condition none
    python scripts/run_rag_eval.py --label wk6-oracle     --condition oracle
    python scripts/run_rag_eval.py --label eval-run-003   --import-label   # refusal check on stored W5 answers
"""
import argparse
import asyncio
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_eval import candidate_text
from src.eval.golden import load_golden
from src.eval.judge import RUBRIC_VERSION, judge_one
from src.eval.rag_metrics import (classify_refusal, judge_citation_support, load_golden_sources,
                                  oracle_hits, retrieval_hit)
from src.pipeline.answer_store import connect, save_eval_run, save_rag_run
from src.pipeline.llm import ask_llm
from src.pipeline.models import Question
from src.pipeline.settings import Settings
from src.rag.naive_rag import cited_sources, load_index, rag_answer, rag_stream_answer
from src.rag.prompt import format_context


def _brief(hits: list[dict]) -> list[dict]:
    return [{k: h[k] for k in ("chunk_id", "source", "page_start", "page_end", "score")} for h in hits]


async def answer_one(entry, args, settings, index, expected):
    """One golden question under the chosen condition → (Answer, hits, latency)."""
    t0 = time.perf_counter()
    if args.condition in ("rag", "rag-stream"):
        fn = rag_answer if args.condition == "rag" else rag_stream_answer
        result = await fn(entry.question, index, settings, args.k)
        return result.answer, result.hits, result.latency_s
    if args.condition == "oracle":
        hits = oracle_hits(expected, args.corpus)
        answer = await ask_llm(Question(question=entry.question), settings, context=format_context(hits))
        answer.sources = cited_sources(answer, hits)
        return answer, hits, time.perf_counter() - t0
    answer = await ask_llm(Question(question=entry.question), settings)
    return answer, [], time.perf_counter() - t0


async def run(args) -> int:
    settings = Settings()
    entries = load_golden(args.golden_set)
    sources = load_golden_sources(args.sources)
    with connect(args.db) as conn:
        if conn.execute("SELECT COUNT(*) FROM rag_runs WHERE label = ?", (args.label,)).fetchone()[0]:
            print(f"label {args.label!r} already has rag_runs rows; pick a new --label")
            return 1
    if args.import_label:
        return await import_label(args, entries)
    retrieves = args.condition in ("rag", "rag-stream")
    if retrieves and not args.index:
        raise SystemExit(f"--condition {args.condition} needs --index")
    index = load_index(args.index) if retrieves else None
    meta = index.meta if index else {}
    print(f"{args.label}: condition={args.condition} index={args.index or '-'} k={args.k} "
          f"model={settings.model} prompt={settings.system_prompt_file} judge={'on' if args.judge else 'off'} "
          f"support={'on' if args.support else 'off'}\n")
    start = time.perf_counter()
    for e in entries:
        expected = sources[e.id]
        answer, hits, latency = await answer_one(e, args, settings, index, expected)
        declined, eval_cost = await classify_refusal(e.question, answer.content)
        support = detail = None
        if hits and args.support and not declined:
            detail, c = await judge_citation_support(e.question, format_context(hits), answer.content)
            support, eval_cost = detail["support"], eval_cost + c
        hit_doc, hit_page = retrieval_hit(hits, expected) if retrieves else (None, None)
        with connect(args.db) as conn:
            save_rag_run(conn, label=args.label, golden_id=e.id, condition=args.condition,
                         index_name=args.index, chunk_size=meta.get("chunk_size"),
                         chunk_overlap=meta.get("chunk_overlap"), k=args.k if hits else None,
                         question=e.question, answer=answer.content, cited=answer.sources,
                         retrieved=_brief(hits), hit_doc=hit_doc, hit_page=hit_page,
                         declined=int(declined), support=support, support_detail=detail,
                         latency_s=round(latency, 3), candidate_cost_usd=answer.cost_usd,
                         eval_cost_usd=eval_cost)
        verdict = ""
        if args.judge:
            cand = candidate_text(answer.model_dump())
            score = await judge_one(e.question, e.ideal_answer, cand)
            with connect(args.db) as conn:
                save_eval_run(conn, golden_id=e.id, question=e.question, candidate_answer=cand,
                              ideal_answer=e.ideal_answer, candidate_model=settings.model,
                              judge_model=score.judge_model, accuracy=score.accuracy,
                              groundedness=score.groundedness, format=score.format,
                              reasoning=score.reasoning, eval_run_label=args.label,
                              candidate_cost_usd=answer.cost_usd, judge_cost_usd=score.cost_usd)
            verdict = f" a={score.accuracy} g={score.groundedness}"
        hit = "" if hit_doc is None else f" hit={'D' if hit_doc else '-'}{'P' if hit_page else '-'}"
        print(f"  {e.id} [{e.bucket:6}]{hit} declined={int(declined)} support={support or '-':7}{verdict}"
              f" {latency:5.2f}s  {e.question[:50]}")
    print(f"\n{args.label} done in {time.perf_counter() - start:.0f}s (rubric {RUBRIC_VERSION}). "
          f"KPIs: python scripts/compute_kpis.py --label {args.label}")
    return 0


async def import_label(args, entries) -> int:
    """Bring stored W5 answers (eval_runs) into rag_runs as condition 'none', with a refusal check.

    Latency and retrieval weren't recorded for them, so those stay empty.
    """
    with sqlite3.connect(args.db) as conn:
        rows = dict(conn.execute("SELECT golden_id, candidate_answer FROM eval_runs WHERE eval_run_label = ?",
                                 (args.label,)).fetchall())
    if not rows:
        raise SystemExit(f"no eval_runs rows for {args.label!r}")
    for e in entries:
        text = rows[e.id].split("\n\nSources given:")[0]
        declined, cost = await classify_refusal(e.question, text)
        with connect(args.db) as conn:
            save_rag_run(conn, label=args.label, golden_id=e.id, condition="none", question=e.question,
                         answer=text, cited=[], retrieved=[], declined=int(declined), eval_cost_usd=cost)
        print(f"  {e.id} declined={int(declined)}  {e.question[:60]}")
    return 0


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="W6: golden set through rag / none / oracle, with DR #1 measures")
    p.add_argument("--label", required=True)
    p.add_argument("--condition", choices=("rag", "rag-stream", "none", "oracle"), default="rag")
    p.add_argument("--index", help="index path prefix, e.g. data/index/medium (condition rag)")
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--judge", action=argparse.BooleanOptionalAction, default=True,
                   help="score accuracy with the W5 judge (gpt-4o, rubric v2)")
    p.add_argument("--support", action=argparse.BooleanOptionalAction, default=True,
                   help="judge citation support (gpt-4o) when the answer had passages")
    p.add_argument("--import-label", action="store_true",
                   help="instead of answering: import a stored W5 label from eval_runs as condition 'none'")
    p.add_argument("--golden-set", default="data/golden_set.jsonl")
    p.add_argument("--sources", default="data/golden_sources.json")
    p.add_argument("--corpus", default="data/corpus/raw")
    p.add_argument("--db", default="data/answers.db")
    return p.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))
