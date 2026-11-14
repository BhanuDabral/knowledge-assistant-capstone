"""src/eval/rag_metrics.py — the W6 RAG measures, including the four DR #1 asked for.

Deterministic:
  • retrieval_hit()      — did top-K contain the expected document / page?
  • oracle_hits()        — the cited golden pages, as passages (oracle-evidence condition)
  • nearest_rank()       — percentile for latency p50 / p95

LLM-judged (JSON mode, temperature 0):
  • classify_refusal()   — did the answer decline? (gpt-4o-mini: a yes/no reading task)
  • judge_citation_support() — are the answer's claims supported by the passages it
                           was given? (gpt-4o: the judge stays stronger than the candidate)

The W5 judge (src/eval/judge.py, rubric v2) still scores accuracy against the
ideal answer; these add what that rubric can't see.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
from pathlib import Path

from openai import AsyncOpenAI

from src.pipeline.cost import compute_cost_usd
from src.pipeline.llm import _client
from src.pipeline.settings import Settings
from src.rag.naive_rag import doc_slug, read_pages

logger = logging.getLogger(__name__)

REFUSAL_MODEL = "gpt-4o-mini"
SUPPORT_MODEL = "gpt-4o"
SUPPORT_LEVELS = ("full", "partial", "none")


# ─── Expected sources ────────────────────────────────────────────────────────

def load_golden_sources(path: str | Path = "data/golden_sources.json") -> dict:
    """{golden_id: {"sources": [{"doc", "pages"}], "out_of_scope": bool}}; skips the _about note."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def retrieval_hit(hits: list[dict], expected: dict) -> tuple[bool | None, bool | None]:
    """(document hit, page hit) for an answerable entry; (None, None) when out of scope.

    Document hit: any retrieved chunk comes from an expected document (the course KPI).
    Page hit (stricter): a retrieved chunk's page span overlaps an expected page.
    """
    if expected.get("out_of_scope"):
        return None, None
    doc_hit = page_hit = False
    for h in hits:
        for src in expected["sources"]:
            if h["source"] == src["doc"]:
                doc_hit = True
                if any(h["page_start"] <= p <= h["page_end"] for p in src["pages"]):
                    page_hit = True
    return doc_hit, page_hit


def oracle_hits(expected: dict, corpus_dir: str | Path = "data/corpus/raw") -> list[dict]:
    """The golden entry's cited pages as passages: what perfect retrieval would hand the model."""
    hits = []
    for src in expected["sources"]:
        pages = read_pages(Path(corpus_dir) / src["doc"])
        for p in src["pages"]:
            hits.append({"chunk_id": f"{doc_slug(src['doc'])}:p{p}:oracle", "source": src["doc"],
                         "page_start": p, "page_end": p, "text": pages[p - 1], "score": 1.0})
    return hits


def nearest_rank(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile (same definition as scripts/stress_test.py)."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(1, math.ceil(pct / 100 * len(ordered))) - 1]


# ─── LLM-judged measures ─────────────────────────────────────────────────────

REFUSAL_PROMPT = """You read one answer from a question-answering assistant and decide whether it DECLINED.
DECLINED = it says it doesn't know, can't find the information, or that the documents don't cover the \
question, and gives no substantive answer to what was asked (pointing to where to look still counts \
as declined). An answer that gives the information, even partly or with a caveat, is NOT declined.
Reply with JSON only: {"declined": true|false}"""

SUPPORT_PROMPT = """You check whether an answer is supported by the passages it was given. Judge ONLY \
against the PASSAGES, not your own knowledge: a true statement that the passages don't contain is \
unsupported.
- "full": every factual claim in the answer is stated in, or directly follows from, the passages.
- "partial": some claims are supported, at least one is not.
- "none": the main claims are not in the passages.
Reply with JSON only: {"support": "full"|"partial"|"none", "unsupported_claims": [short strings], \
"reasoning": "one or two sentences"}"""


async def _json_call(client: AsyncOpenAI, model: str, system: str, user: str) -> tuple[dict, float]:
    """One JSON-mode call with one retry. Returns (parsed JSON, cost)."""
    for attempt in (1, 2):
        try:
            resp = await client.chat.completions.create(
                model=model, temperature=0, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
            usage = resp.usage
            cost = compute_cost_usd(model, usage.prompt_tokens, usage.completion_tokens) if usage else 0.0
            return json.loads(resp.choices[0].message.content), cost
        except Exception as exc:
            if attempt == 2:
                raise
            logger.warning("%s call failed: %s; retrying", model, exc)
            await asyncio.sleep(1.0)
    raise RuntimeError("unreachable")


async def classify_refusal(question: str, answer: str, client: AsyncOpenAI | None = None) -> tuple[bool, float]:
    """(declined?, cost)."""
    client = client or _client(Settings(model=REFUSAL_MODEL))
    data, cost = await _json_call(client, REFUSAL_MODEL, REFUSAL_PROMPT,
                                  f"QUESTION:\n{question}\n\nANSWER:\n{answer}")
    return bool(data.get("declined")), cost


async def judge_citation_support(question: str, passages: str, answer: str,
                                 client: AsyncOpenAI | None = None) -> tuple[dict, float]:
    """({"support", "unsupported_claims", "reasoning"}, cost). support is one of SUPPORT_LEVELS."""
    client = client or _client(Settings(model=SUPPORT_MODEL))
    data, cost = await _json_call(client, SUPPORT_MODEL, SUPPORT_PROMPT,
                                  f"QUESTION:\n{question}\n\nPASSAGES:\n{passages}\n\nANSWER:\n{answer}")
    if data.get("support") not in SUPPORT_LEVELS:
        raise ValueError(f"citation judge returned {data.get('support')!r}")
    return data, cost
