"""tests/test_w4_capstone.py — capstone tests for the W4 additions not covered by the course tests.

All offline: fake LLM (conftest) or a mocked OpenAI client. No API key, no cost.
"""
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from src.pipeline.llm import PromptTooLong, ask_llm, check_prompt_size, count_prompt_tokens, stream_answer
from src.pipeline.models import Question
from src.pipeline.settings import Settings

client = TestClient(app)


# ─── tiktoken guard ──────────────────────────────────────────────────────────
def test_count_prompt_tokens_matches_tiktoken():
    assert count_prompt_tokens("What is RAG?", "gpt-4o-mini") == 5


def test_unknown_model_falls_back_to_o200k():
    assert count_prompt_tokens("What is RAG?", "llama3.2:3b") == 5


def test_guard_raises_over_limit():
    with pytest.raises(PromptTooLong):
        check_prompt_size("word " * 50, Settings(max_input_tokens=10))


def test_api_rejects_long_question_with_422_and_no_llm_call():
    with patch("src.pipeline.llm.fake_ask_llm", AsyncMock()) as m:
        r = client.post("/ask_batched", json={"question": "word " * 2500})
    assert r.status_code == 422
    assert r.json()["detail"][0]["type"] == "too_many_tokens"
    assert m.call_count == 0


# ─── Real path, mocked client: tool-call parse + cost from usage ────────────
def _fake_resp(args_json, prompt_tokens, completion_tokens):
    call = SimpleNamespace(function=SimpleNamespace(arguments=args_json))
    msg = SimpleNamespace(tool_calls=[call])
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)],
                           usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens))


@pytest.mark.asyncio
async def test_real_path_builds_answer_and_real_cost():
    resp = _fake_resp('{"content": "FEAT = Fairness, Ethics, Accountability, Transparency.", '
                      '"confidence": 0.8, "sources": ["MAS FEAT 2018"]}', 100, 50)
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=resp))))
    settings = Settings(use_fake=False, model="gpt-4o-mini", openai_api_key="not-used")
    with patch("src.pipeline.llm._client", return_value=fake_client):
        ans = await ask_llm(Question(question="What is FEAT?"), settings)
    assert ans.sources == ["MAS FEAT 2018"] and ans.confidence == 0.8
    assert ans.cost_usd == pytest.approx(45 / 1_000_000)        # 100×0.15 + 50×0.60 per 1M
    assert ans.schema_version == "v1" and ans.retries == 0


# ─── Streaming + persistence ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_stream_answer_fake_yields_chunks():
    chunks = [c async for c in stream_answer("What is RAG?", Settings(use_fake=True))]
    assert len(chunks) > 1 and "".join(chunks).startswith("[FAKE]")


def test_ask_batched_saves_row_labelled_fake(_isolated_answers_db):
    r = client.post("/ask_batched", json={"question": "What is RAG?"})
    assert r.status_code == 200
    rows = sqlite3.connect(_isolated_answers_db).execute(
        "SELECT question, model, schema_version FROM answers").fetchall()
    assert rows == [("What is RAG?", "fake", "v1")]
