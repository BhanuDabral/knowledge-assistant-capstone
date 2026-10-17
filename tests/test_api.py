"""tests/test_api.py — REFERENCE for Week 3 Lab Step 2 sub-step 2b (API tests).

Uses FastAPI's TestClient. No mocking needed for these — they test the
validation surface, not the LLM. The underlying W2 pipeline runs in
`use_fake=True` mode (the default) so any actual /ask call would use canned
fake answers — but these tests never reach an LLM call.

Run with:
    pytest tests/test_api.py -v
"""
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from api.main import app
from src.pipeline.fake_llm import Answer as _PipelineAnswer, FakeLLMError


client = TestClient(app)


def test_ask_rejects_missing_question():
    """POST /ask with empty body -> 422 Unprocessable Entity."""
    response = client.post("/ask", json={})
    assert response.status_code == 422
    body = response.json()
    detail_text = str(body.get("detail", ""))
    assert "question" in detail_text.lower()



def test_ask_rejects_empty_question():
    """POST /ask with an empty question -> 422 (min_length=1), before any LLM call."""
    response = client.post("/ask", json={"question": ""})
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "string_too_short"

def test_health_returns_ok():
    """GET /health -> 200 OK with the expected body."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_batched_retries_transient_failure():
    """One transient LLM failure is retried: 200, and the Answer reports retries=1."""
    ok = _PipelineAnswer(question="q", text="Recovered answer.", cost_usd=0.0001)
    with patch("src.pipeline.pipeline.fake_ask_llm",
               AsyncMock(side_effect=[FakeLLMError("transient"), ok])) as m, \
         patch("src.pipeline.pipeline.asyncio.sleep", AsyncMock()):
        response = client.post("/ask_batched", json={"question": "What is FEAT?"})
    assert response.status_code == 200
    assert response.json() == {"content": "Recovered answer.", "cost_usd": 0.0001, "retries": 1}
    assert m.call_count == 2

