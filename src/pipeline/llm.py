"""src/pipeline/llm.py — Week 4 LLM layer (tool-calling, structured Answer).

Based on the course reference W4 `pipeline.py`. Kept in its own module so the
W2 batch pipeline (`pipeline.py`) and its W3 tests keep working unchanged.

  • ask_llm: tool-calling → structured Answer (content, confidence, sources,
    schema_version="v1"), with retry + exponential backoff.

Run the fake path (no API key, no cost) with PIPELINE_USE_FAKE=1.
"""
from __future__ import annotations

import asyncio
import json
import logging

from openai import AsyncOpenAI

from .models import Answer, Question
from .settings import Settings

logger = logging.getLogger(__name__)


# ─── Tool schema for structured outputs (Lab 1b) ───────────────────────────
ANSWER_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "answer_question",
        "description": "Return a structured answer with content, confidence, and sources.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The answer in 2-4 sentences."},
                "confidence": {
                    "type": "number",
                    "description": "How confident you are in the answer, 0.0 to 1.0.",
                },
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Source identifiers or URLs you used. Empty list is fine "
                        "if you used general knowledge."
                    ),
                },
            },
            "required": ["content", "confidence", "sources"],
        },
    },
}


# ─── Fake LLM (tests + offline runs) ────────────────────────────────────────
async def fake_ask_llm(question: str) -> str:
    """Returns a canned answer with a small delay."""
    await asyncio.sleep(0.05)
    return f"[FAKE] {question[:60]}"


def _client(settings: Settings) -> AsyncOpenAI:
    key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
    return AsyncOpenAI(api_key=key)


async def _call_once(q: Question, settings: Settings) -> Answer:
    """One attempt: fake path, or a real tool-calling request."""
    if settings.use_fake:
        return Answer(content=await fake_ask_llm(q.question), cost_usd=0.0)

    resp = await _client(settings).chat.completions.create(
        model=settings.model,
        messages=[{"role": "user", "content": q.question}],
        tools=[ANSWER_TOOL],
        # Force OUR tool; without this the model may just reply in text.
        tool_choice={"type": "function", "function": {"name": "answer_question"}},
    )
    tool_calls = resp.choices[0].message.tool_calls or []
    if not tool_calls:
        raise RuntimeError("LLM did not call the answer_question tool")
    args = json.loads(tool_calls[0].function.arguments)    # a JSON string, not a dict
    return Answer(
        content=args["content"],
        confidence=args["confidence"],
        sources=args.get("sources", []),
        cost_usd=0.0001,                                    # placeholder until Lab Step 2
        schema_version="v1",
    )


# ─── Tool-calling ask_llm with retry (Lab 1d, 1e) ──────────────────────────
async def ask_llm(q: Question, settings: Settings | None = None) -> Answer:
    """Structured Answer via tool-calling; retries transient failures."""
    settings = settings or Settings()
    for attempt in range(settings.max_retries + 1):
        try:
            ans = await _call_once(q, settings)
            ans.retries = attempt
            return ans
        except Exception as exc:
            if attempt == settings.max_retries:
                raise
            logger.warning("ask_llm attempt %d failed: %s; retrying", attempt + 1, exc)
            await asyncio.sleep(settings.retry_delay_s * (2 ** attempt))
    raise RuntimeError("unreachable")
