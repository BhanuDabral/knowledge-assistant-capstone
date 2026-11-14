"""api/main.py — Capstone API (W3 contract, W4 internals).

Public contract locked in ADR 0002: Question {question} → Answer
{content, cost_usd, retries} + W4 additive fields {confidence, sources,
schema_version}. Endpoints: POST /ask (stream), POST /ask_batched, GET /health,
GET /metrics (internal).

W4: /ask_batched uses tool-calling (src/pipeline/llm.py) for a structured Answer
with real cost, saved to data/answers.db; /ask streams real LLM tokens; a
tiktoken guard rejects over-long questions with 422 before any LLM call.

W6: naive RAG. When PIPELINE_RAG_INDEX is set, both /ask_batched and /ask
retrieve the top-K chunks first and answer from them (src/rag/naive_rag.py).
`sources` now holds the chunk ids the model cited; /ask ends its stream with
the retrieved passages. The contract is unchanged (schema v1).
"""
import logging
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

# Public models — shared with the pipeline since W4 (src/pipeline/models.py)
from src.pipeline.models import Answer, Question
from src.pipeline.llm import PromptTooLong, ask_llm, check_prompt_size, stream_answer
from src.pipeline.settings import Settings
from src.pipeline.answer_store import connect, save_answer
from src.rag.naive_rag import RagIndex, rag_answer, retrieve
from src.rag.qdrant_store import QDRANT_PREFIX, open_index
from src.rag.prompt import format_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Capstone API — Singapore AI & Data Governance Assistant",
    description=(
        "Q&A over Singapore AI and data governance frameworks (IMDA, PDPC, MAS). "
        "Structured answers via tool-calling (W4); contract locked in ADR 0002."
    ),
    version="1.0.0",
)

_settings = Settings()        # read once at startup (model, use_fake, retries, key)


def _load_rag_index(settings: Settings):
    """The index, opened once at startup: a Qdrant collection ("qdrant:<name>", W7) or a W6 NumPy
    index path. A configured but missing index stops the server loudly."""
    if settings.rag_index is None:
        log.info("retrieval off (PIPELINE_RAG_INDEX not set): answers come from the model alone")
        return None
    spec = str(settings.rag_index)
    if not spec.startswith(QDRANT_PREFIX) and not settings.rag_index.with_suffix(".npy").exists():
        raise RuntimeError(f"PIPELINE_RAG_INDEX={spec} but no index there; "
                           f"run: python scripts/build_index.py --out {spec}")
    index = open_index(spec)
    log.info("retrieval on: %d chunks from %s (%s), k=%d", len(index), spec,
             index.meta.get("backend", "numpy"), settings.rag_k)
    return index


_index = _load_rag_index(_settings)


def _too_long(exc: PromptTooLong, question: str) -> HTTPException:
    """422 in the same {"detail": [...]} shape FastAPI uses for validation errors."""
    return HTTPException(status_code=422, detail=[{
        "type": "too_many_tokens", "loc": ["body", "question"],
        "msg": str(exc), "input": question[:80] + ("…" if len(question) > 80 else ""),
    }])


# ─────────────────────────────────────────────────────────────────────────────
# W3 activity — request counter middleware (in memory; resets on restart)
# ─────────────────────────────────────────────────────────────────────────────
request_counts: dict[str, int] = {}


@app.middleware("http")
async def count_requests(request, call_next):
    """Count every request by path before passing it on to the endpoint."""
    path = request.url.path
    request_counts[path] = request_counts.get(path, 0) + 1
    response = await call_next(request)
    return response


# ─────────────────────────────────────────────────────────────────────────────
# /ask_batched — structured Answer (tool-calling), saved to data/answers.db
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/ask_batched", response_model=Answer)
async def ask_batched(q: Question) -> Answer:
    """Structured Answer via tool-calling (W4), saved to data/answers.db."""
    log.info("ask_batched  question=%r", q.question[:80])
    try:
        if _index is not None:                              # W6: retrieve, then answer from the passages
            answer = (await rag_answer(q.question, _index, _settings, _settings.rag_k)).answer
        else:
            answer = await ask_llm(q, _settings)
    except PromptTooLong as exc:
        raise _too_long(exc, q.question)
    with connect(_settings.answers_db) as conn:
        save_answer(
            conn, question=q.question, content=answer.content, retries=answer.retries,
            cost_usd=answer.cost_usd,
            # The course code recorded settings.model even for fake answers; label them honestly.
            model="fake" if _settings.use_fake else _settings.model,
            confidence=answer.confidence, sources=answer.sources,
            schema_version=answer.schema_version,
        )
    return answer


# ─────────────────────────────────────────────────────────────────────────────
# /health — liveness probe
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# /ask — streamed text/plain, real LLM tokens (W4)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/ask")
async def ask(q: Question):
    """Streaming /ask — the contracted endpoint. Real LLM tokens since W4."""
    log.info("ask  question=%r", q.question[:80])
    try:
        check_prompt_size(q.question, _settings)            # reject before the stream starts
    except PromptTooLong as exc:
        raise _too_long(exc, q.question)
    if _index is None:
        return StreamingResponse(stream_answer(q.question, _settings), media_type="text/plain")
    hits, _ = await retrieve(q.question, _index, _settings, _settings.rag_k)
    return StreamingResponse(_stream_with_passages(q.question, hits), media_type="text/plain")


async def _stream_with_passages(question: str, hits: list[dict]) -> AsyncIterator[str]:
    """The streamed answer, then the passages it was given (a stream can't carry a sources field)."""
    async for token in stream_answer(question, _settings, context=format_context(hits)):
        yield token
    yield "\n\n---\nRetrieved passages:\n" + "\n".join(
        f"- [{h['chunk_id']}] {h['source']}, p.{h['page_start']}"
        + (f"-{h['page_end']}" if h["page_end"] != h["page_start"] else "") + f" (score {h['score']:.2f})"
        for h in hits)


# ─────────────────────────────────────────────────────────────────────────────
# W3 activity — /metrics: per-path request counts since the process started
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/metrics")
async def metrics():
    return {
        "endpoints": request_counts,
        "total": sum(request_counts.values()),
        # W6: is retrieval on? (/health stays exactly {"status": "ok"}: the W3 contract test pins it)
        "retrieval": ({"chunks": len(_index), "k": _settings.rag_k, "index": str(_settings.rag_index)}
                      if _index is not None else None),
    }
