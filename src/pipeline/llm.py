"""src/pipeline/llm.py — Week 4 LLM layer (tool-calling, structured Answer).

Based on the course reference W4 `pipeline.py`. Kept in its own module so the
W2 batch pipeline (`pipeline.py`) and its W3 tests keep working unchanged.

  • ask_llm: tool-calling → structured Answer (content, confidence, sources,
    schema_version="v1"), with retry + exponential backoff.
  • Real cost_usd from response.usage via cost.py (Lab 2c/2d).
  • stream_answer: real OpenAI streaming, no simulated sleep (Lab 2a/2b).
  • check_prompt_size: tiktoken pre-call guard (deck slide 8; not in the
    course reference code).
  • Local models via Ollama (W4 take-home): same code path, different base_url
    (course `ollama_integration_snippet.py`, corrected version).

Run the fake path (no API key, no cost) with PIPELINE_USE_FAKE=1.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

import tiktoken
from openai import AsyncOpenAI

from .cost import compute_cost_usd
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


# ─── Pre-call token guard (tiktoken) ────────────────────────────────────────
class PromptTooLong(ValueError):
    """The question has more tokens than Settings.max_input_tokens."""


def count_prompt_tokens(text: str, model: str) -> int:
    """Tokens in `text` for `model`. Non-OpenAI models fall back to o200k_base (approximate)."""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("o200k_base")
    return len(enc.encode(text))


def check_prompt_size(text: str, settings: Settings) -> int:
    """Raise PromptTooLong before any API call if the question is over budget."""
    n = count_prompt_tokens(text, settings.model)
    if n > settings.max_input_tokens:
        raise PromptTooLong(f"question has {n} tokens; limit is {settings.max_input_tokens}")
    return n


# ─── Local models via Ollama (W4 activity) ─────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434/v1"
# One explicit list (not a name-prefix guess) of models routed to Ollama.
LOCAL_MODELS = frozenset({"llama3.2:3b", "llama3.1:8b", "qwen2.5:7b", "mistral:7b"})

# Structured-output fallback for local models that skip the tool call.
_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "confidence": {"type": "number"},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["content", "confidence", "sources"],
    "additionalProperties": False,
}


def is_local(model: str) -> bool:
    return model.removeprefix("ollama:") in LOCAL_MODELS


# ─── Fake LLM (tests + offline runs) ────────────────────────────────────────
async def fake_ask_llm(question: str) -> str:
    """Returns a canned answer with a small delay."""
    await asyncio.sleep(0.05)
    return f"[FAKE] {question[:60]}"


def system_messages(settings: Settings) -> list[dict]:
    """The versioned system prompt as a message list; [] when none is configured (W4 behaviour)."""
    if settings.system_prompt_file is None:
        return []
    return [{"role": "system", "content": settings.system_prompt_file.read_text(encoding="utf-8").strip()}]


def _client(settings: Settings) -> AsyncOpenAI:
    """OpenAI, or Ollama's OpenAI-compatible endpoint for local models."""
    if is_local(settings.model):
        return AsyncOpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")   # key required by the SDK, ignored by Ollama
    key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
    return AsyncOpenAI(api_key=key)


async def _call_once(q: Question, settings: Settings) -> Answer:
    """One attempt: fake path, or a real tool-calling request."""
    if settings.use_fake:
        return Answer(content=await fake_ask_llm(q.question), cost_usd=0.0)

    local = is_local(settings.model)
    client = _client(settings)
    model = settings.model.removeprefix("ollama:")
    request = {
        "model": model,
        "messages": system_messages(settings) + [{"role": "user", "content": q.question}],
        "tools": [ANSWER_TOOL],
    }
    if not local:
        # Force OUR tool; without this the model may just reply in text.
        # (Ollama does not support tool_choice, so it's omitted there.)
        request["tool_choice"] = {"type": "function", "function": {"name": "answer_question"}}
    resp = await client.chat.completions.create(**request)
    tool_calls = resp.choices[0].message.tool_calls or []
    if tool_calls:
        args = json.loads(tool_calls[0].function.arguments)    # a JSON string, not a dict
    elif local:
        # Small local models comply with tool-calling inconsistently: fall back to
        # schema-constrained JSON (Ollama >= 0.5) and say so, rather than failing silently.
        logger.info("model %s returned no tool call; using structured output", model)
        resp = await client.chat.completions.create(
            model=model,
            messages=system_messages(settings)
                     + [{"role": "system", "content": "Answer the question using the provided schema."},
                        {"role": "user", "content": q.question}],
            response_format={"type": "json_schema", "json_schema": {
                "name": "answer_question", "schema": _ANSWER_SCHEMA, "strict": True}},
        )
        args = json.loads(resp.choices[0].message.content)
        args["confidence"] = max(0.0, min(1.0, float(args["confidence"])))   # strict mode checks shape, not range
    else:
        raise RuntimeError("LLM did not call the answer_question tool")
    usage = resp.usage                                      # what you were actually billed for
    cost = compute_cost_usd(settings.model,
                            usage.prompt_tokens if usage else 0,
                            usage.completion_tokens if usage else 0)
    return Answer(
        content=args["content"],
        confidence=args["confidence"],
        sources=args.get("sources", []),
        cost_usd=cost,
        schema_version="v1",
    )


# ─── Tool-calling ask_llm with retry (Lab 1d, 1e) ──────────────────────────
async def ask_llm(q: Question, settings: Settings | None = None) -> Answer:
    """Structured Answer via tool-calling; retries transient failures."""
    settings = settings or Settings()
    check_prompt_size(q.question, settings)                 # before any cost; never retried
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


# ─── Real streaming (Lab 2a, 2b) ────────────────────────────────────────────
async def stream_answer(question: str, settings: Settings | None = None) -> AsyncIterator[str]:
    """Yield content tokens as they arrive from the LLM. No sleep, no word-splitting.

    The guard runs when the stream starts. A stream can't be retried part-way
    (deck slide 28); a failure cuts the stream short.
    """
    settings = settings or Settings()
    check_prompt_size(question, settings)

    if settings.use_fake:
        full = await fake_ask_llm(question)
        for word in full.split(" "):
            await asyncio.sleep(0.05)
            yield word + " "
        return

    stream = await _client(settings).chat.completions.create(
        model=settings.model.removeprefix("ollama:"),
        messages=system_messages(settings) + [{"role": "user", "content": question}],
        stream=True,
        stream_options={"include_usage": True},             # last chunk carries usage
    )
    async for chunk in stream:
        if chunk.usage:                                     # final, content-free chunk
            cost = compute_cost_usd(settings.model, chunk.usage.prompt_tokens,
                                    chunk.usage.completion_tokens)
            logger.info("stream done  model=%s  in=%d out=%d  cost_usd=%.6f", settings.model,
                        chunk.usage.prompt_tokens, chunk.usage.completion_tokens, cost)
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content

