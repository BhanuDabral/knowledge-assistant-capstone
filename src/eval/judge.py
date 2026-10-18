"""src/eval/judge.py — LLM-as-judge with a rubric (W5 Lab Step 3).

Written by Claude Code from the W5 lab guide's spec and `judge_demo.ipynb`
(the course bundle's judge starter/reference were not available). The three
lab TODOs are marked: 3a RUBRIC_PROMPT, 3b the client call, 3c parsing.

judge_one() scores a candidate answer against the golden ideal answer on three
dimensions (1-4): accuracy, groundedness, format. The judge is the STRONG model
(gpt-4o); the candidate is the app's model (gpt-4o-mini). Tool-calling forces a
structured verdict — the same W4 pattern as ask_llm's ANSWER_TOOL.
"""
from __future__ import annotations

import asyncio
import json
import logging

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.pipeline.cost import compute_cost_usd
from src.pipeline.llm import _client
from src.pipeline.settings import Settings

logger = logging.getLogger(__name__)

JUDGE_MODEL = "gpt-4o"            # judge stronger than judged; never fall back to the candidate model
RUBRIC_VERSION = "v2"             # v1: eval-run-001 · v2: sharpened after the blind calibration (docs/judge-calibration.md)

# ─── 3a: the rubric prompt ──────────────────────────────────────────────────
RUBRIC_PROMPT = """You are a senior evaluator for a question-answering assistant on Singapore AI and data \
governance frameworks published by IMDA, PDPC and MAS. Its users are compliance and risk analysts who \
will quote the answer in their work, so a confident wrong answer is worse than an honest "I don't know".

You receive a QUESTION, an IDEAL answer written from the source document, and a CANDIDATE answer. \
Score the CANDIDATE on three dimensions, each 1-4. Judge substance, not style: do not reward length, \
confidence or polish.

ACCURACY — are the facts in the candidate correct and complete compared with the IDEAL?
  4 = every fact in the ideal is present and correct, with no subtle substitutions, conflations or wrong numbers
  3 = the main facts are correct; one minor detail is missing or imprecise, and nothing would mislead a careful reader
  2 = partly correct: at least one fact from the ideal is present, but a required fact is missing or a claim is wrong \
(e.g. lists 3 of 4 conditions, or swaps an item)
  1 = wrong or does not answer: none of the ideal's facts is present, or the main claim contradicts the ideal

GROUNDEDNESS — is every claim supported by the IDEAL / the named framework, with nothing invented?
  4 = every claim is supported; no invented principles, sections, document names, figures or sources
  3 = supported overall, plus harmless general context that the ideal does not mention. Generic statements \
not tied to any document (e.g. "this builds trust", "requirements vary by organisation") are harmless context, not inventions
  2 = at least one invented specific: a named list item, section, figure, framework, document or source that is not in the ideal
  1 = largely invented, or contradicts the ideal; for out-of-scope questions, answers instead of declining
  When the IDEAL says the documents do not cover the question, a candidate that clearly declines and points \
to an appropriate source scores 4; one that supplies specific facts, names or figures scores 1 or 2.

FORMAT — is it a usable answer for this user? Score usability ONLY, independent of whether the content is \
correct: a wrong answer can still be well formatted (wrong content is penalised under ACCURACY and GROUNDEDNESS, never here).
  4 = answers directly in about 2-4 sentences (or a short list for enumerations), plain English, names the framework it draws on
  3 = answers, but is padded, slightly too long or too short, or does not name the framework
  2 = the answer is buried in hedging or generic text and is hard to use
  1 = unusable: off-topic, empty, or mostly filler

Give a short reasoning (2-4 sentences) that cites the specific facts you checked, missing items, or invented claims.
ALWAYS call the rate_answer tool. Never reply in plain text."""

JUDGE_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "rate_answer",
        "description": "Submit the rubric scores and reasoning for the candidate answer.",
        "parameters": {
            "type": "object",
            "properties": {
                "accuracy": {"type": "integer", "minimum": 1, "maximum": 4},
                "groundedness": {"type": "integer", "minimum": 1, "maximum": 4},
                "format": {"type": "integer", "minimum": 1, "maximum": 4},
                "reasoning": {"type": "string", "description": "2-4 sentences citing specific facts."},
            },
            "required": ["accuracy", "groundedness", "format", "reasoning"],
        },
    },
}


class JudgeScore(BaseModel):
    """One judge verdict. Pydantic enforces the 1-4 range the tool schema asks for."""
    accuracy: int = Field(ge=1, le=4)
    groundedness: int = Field(ge=1, le=4)
    format: int = Field(ge=1, le=4)
    reasoning: str = Field(min_length=10)
    judge_model: str = JUDGE_MODEL
    cost_usd: float = 0.0

    @property
    def mean(self) -> float:
        return (self.accuracy + self.groundedness + self.format) / 3


def build_messages(question: str, ideal_answer: str, candidate: str) -> list[dict]:
    """Rubric as the system prompt; the three texts clearly delimited in the user turn."""
    return [
        {"role": "system", "content": RUBRIC_PROMPT},
        {"role": "user", "content": (
            f"QUESTION:\n{question}\n\nIDEAL ANSWER:\n{ideal_answer}\n\nCANDIDATE ANSWER:\n{candidate}"
        )},
    ]


# ─── 3c: parse the tool call into a JudgeScore ──────────────────────────────
def parse_tool_call(resp, model: str = JUDGE_MODEL) -> JudgeScore:
    """Read rate_answer's arguments (a JSON string) and validate them; cost from usage."""
    calls = resp.choices[0].message.tool_calls or []
    if not calls:
        raise RuntimeError("judge did not call rate_answer")
    args = json.loads(calls[0].function.arguments)
    usage = resp.usage
    cost = compute_cost_usd(model, usage.prompt_tokens, usage.completion_tokens) if usage else 0.0
    return JudgeScore(**args, judge_model=model, cost_usd=cost)


# ─── 3b: call the judge ─────────────────────────────────────────────────────
async def judge_one(question: str, ideal_answer: str, candidate: str, *,
                    model: str = JUDGE_MODEL, client: AsyncOpenAI | None = None,
                    attempts: int = 2) -> JudgeScore:
    """Score one candidate. Retries once if the verdict is malformed or the call fails."""
    client = client or _client(Settings(model=model))
    for attempt in range(1, attempts + 1):
        try:
            resp = await client.chat.completions.create(
                model=model,
                temperature=0,                                  # repeatable verdicts
                messages=build_messages(question, ideal_answer, candidate),
                tools=[JUDGE_TOOL],
                tool_choice={"type": "function", "function": {"name": "rate_answer"}},
            )
            return parse_tool_call(resp, model)
        except Exception as exc:
            if attempt == attempts:
                raise
            logger.warning("judge attempt %d failed: %s; retrying", attempt, exc)
            await asyncio.sleep(1.0)
    raise RuntimeError("unreachable")
