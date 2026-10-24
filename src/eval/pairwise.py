"""src/eval/pairwise.py — pairwise comparison with position-bias control (W5 Lab Step 4).

Instead of "score this 1-4", the judge answers "which of these two is better?".
Judges favour whichever answer they see first on close calls (position bias), so
pairwise_compare() asks TWICE — v1 shown first, then v2 shown first — and only
declares a winner when both orders agree. Disagreement is reported as
"ambiguous": the result depended on the order, not the answers.
"""
from __future__ import annotations

import asyncio
import json

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.pipeline.cost import compute_cost_usd
from src.pipeline.llm import _client
from src.pipeline.settings import Settings

PAIRWISE_PROMPT = """You compare two answers from a question-answering assistant on Singapore AI and data \
governance frameworks (IMDA, PDPC, MAS). You receive the QUESTION, an IDEAL answer written from the source \
document, and two candidates, FIRST and SECOND.

Decide which candidate is better for a compliance analyst who will rely on it. In order of importance:
1. Accuracy against the IDEAL: correct, complete facts beat missing or wrong ones.
2. Groundedness: invented names, list items, figures or sources are serious faults. When the IDEAL says the \
documents do not cover the question, an honest "I don't know" beats a confident answer.
3. Usability: direct and concise.

Do NOT prefer an answer because it is longer, more confident or shown first. If both are equally good or \
equally bad, answer "tie". ALWAYS call the pick_winner tool."""

PAIRWISE_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "pick_winner",
        "description": "Say which candidate is better, or tie.",
        "parameters": {
            "type": "object",
            "properties": {
                "winner": {"type": "string", "enum": ["first", "second", "tie"]},
                "reasoning": {"type": "string", "description": "1-3 sentences naming what decided it."},
            },
            "required": ["winner", "reasoning"],
        },
    },
}


class PairwiseVerdict(BaseModel):
    winner: str = Field(pattern="^(first|second|tie)$")
    reasoning: str = Field(min_length=5)
    cost_usd: float = 0.0


async def pairwise_once(question: str, ideal: str, first: str, second: str, *,
                        model: str = "gpt-4o", client: AsyncOpenAI | None = None) -> PairwiseVerdict:
    """One judgement with a fixed order."""
    client = client or _client(Settings(model=model))
    resp = await client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": PAIRWISE_PROMPT},
            {"role": "user", "content": (f"QUESTION:\n{question}\n\nIDEAL ANSWER:\n{ideal}\n\n"
                                         f"FIRST:\n{first}\n\nSECOND:\n{second}")},
        ],
        tools=[PAIRWISE_TOOL],
        tool_choice={"type": "function", "function": {"name": "pick_winner"}},
    )
    calls = resp.choices[0].message.tool_calls or []
    if not calls:
        raise RuntimeError("judge did not call pick_winner")
    u = resp.usage
    cost = compute_cost_usd(model, u.prompt_tokens, u.completion_tokens) if u else 0.0
    return PairwiseVerdict(**json.loads(calls[0].function.arguments), cost_usd=cost)


def _to_label(winner: str, v1_first: bool) -> str:
    """Map 'first'/'second' back to the prompt version that was in that slot."""
    if winner == "tie":
        return "tie"
    return "v1" if (winner == "first") == v1_first else "v2"


def combine(forward: str, reverse: str) -> str:
    """Both orders agree -> that result; otherwise the order decided it -> 'ambiguous'."""
    return forward if forward == reverse else "ambiguous"


async def pairwise_compare(question: str, ideal: str, answer_v1: str, answer_v2: str, *,
                           model: str = "gpt-4o", client: AsyncOpenAI | None = None) -> dict:
    """Judge v1 vs v2 in both orders (concurrently) and combine."""
    fwd, rev = await asyncio.gather(
        pairwise_once(question, ideal, answer_v1, answer_v2, model=model, client=client),  # v1 first
        pairwise_once(question, ideal, answer_v2, answer_v1, model=model, client=client),  # v2 first
    )
    f, r = _to_label(fwd.winner, v1_first=True), _to_label(rev.winner, v1_first=False)
    return {
        "result": combine(f, r),
        "forward": {"winner": f, "reasoning": fwd.reasoning},     # v1 shown first
        "reverse": {"winner": r, "reasoning": rev.reasoning},     # v2 shown first
        "cost_usd": fwd.cost_usd + rev.cost_usd,
    }
