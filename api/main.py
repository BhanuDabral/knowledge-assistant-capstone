"""api/main.py — STARTER for Week 3 Lab Step 1.

You will complete this file across sub-steps 1b → 1f. Each TODO matches a
sub-step in the lab guide.

The completed reference is at <cohort-repo>/week3/reference/api_main_reference.py.

Architecture note: this file holds the *public* W3 API contract — Question
with field `question`, Answer with fields `content/cost_usd/retries`. These
are locked in ADR 0002. Internally we delegate to the W2 pipeline's
`ask_llm`, whose Question has field `text` and whose Answer has field `text`.
The translation happens inside each endpoint.
"""
import asyncio
import logging

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# W2 pipeline — the underlying engine
from src.pipeline.pipeline import ask_llm as _pipeline_ask_llm
from src.pipeline.pipeline import ask_llm_with_retry as _pipeline_ask_llm_with_retry  # 3 tries, 1 s / 2 s backoff
from src.pipeline.pipeline import Question as _PipelineQuestion

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Public W3 API models — locked in ADR 0002
# ─────────────────────────────────────────────────────────────────────────────
class Question(BaseModel):
    """Public request shape. Field name `question`, not `text`."""
    question: str = Field(min_length=1)    # empty string -> 422, no LLM call


class Answer(BaseModel):
    """Public response shape. Field name `content`, not `text`."""
    content: str
    cost_usd: float
    retries: int


# ─────────────────────────────────────────────────────────────────────────────
# 1b — Replace the placeholder below with a real FastAPI app instance.
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Capstone API — Singapore AI & Data Governance Assistant",
    description=(
        "Q&A over Singapore AI and data governance frameworks (IMDA, PDPC, MAS). "
        "Wraps the W2 async pipeline; contract locked in ADR 0002."
    ),
    version="1.0.0",
)


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
# 1c — Add the /ask_batched endpoint (non-streaming reference).
#
# Translate W3 Question → W2 _PipelineQuestion(text=q.question), then call
# _pipeline_ask_llm, then translate the W2 Answer → W3 Answer.
#
# Shape:
#   @app.post("/ask_batched", response_model=Answer)
#   async def ask_batched(q: Question) -> Answer:
#       pipeline_q = _PipelineQuestion(text=q.question)
#       pipeline_ans = await _pipeline_ask_llm(pipeline_q)
#       return Answer(
#           content=pipeline_ans.text,
#           cost_usd=pipeline_ans.cost_usd,
#           retries=pipeline_ans.retries,
#       )
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/ask_batched", response_model=Answer)
async def ask_batched(q: Question) -> Answer:
    """Non-streaming. Returns the full Answer in a single JSON body."""
    log.info("ask_batched  question=%r", q.question[:80])
    pipeline_q = _PipelineQuestion(text=q.question)        # public W3 → internal W2
    pipeline_ans = await _pipeline_ask_llm_with_retry(pipeline_q)
    return Answer(                                          # internal W2 → public W3
        content=pipeline_ans.text,
        cost_usd=pipeline_ans.cost_usd,
        retries=pipeline_ans.retries,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1d — Add /health.
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# 1f — Add stream_answer + the streaming /ask endpoint.
#
# stream_answer(question_text: str) is an async generator that:
#   - builds _PipelineQuestion(text=question_text)
#   - awaits _pipeline_ask_llm to get a full pipeline Answer
#   - yields words from pipeline_ans.text.split(" ") with " " appended
#   - awaits asyncio.sleep(0.05) between yields
#
# The /ask endpoint returns StreamingResponse(stream_answer(q.question), media_type="text/plain").
# ─────────────────────────────────────────────────────────────────────────────

async def stream_answer(question_text: str):
    """Async generator yielding the answer word by word, 50 ms apart.

    W3 streams from FastAPI to the client; the pipeline call itself is still
    non-streaming. In W4 the LLM call becomes a real stream end-to-end.
    """
    pipeline_q = _PipelineQuestion(text=question_text)
    pipeline_ans = await _pipeline_ask_llm_with_retry(pipeline_q)
    for word in pipeline_ans.text.split(" "):
        yield word + " "
        await asyncio.sleep(0.05)


@app.post("/ask")
async def ask(q: Question):
    """Streaming /ask — the contracted endpoint."""
    log.info("ask  question=%r", q.question[:80])
    return StreamingResponse(stream_answer(q.question), media_type="text/plain")


# ─────────────────────────────────────────────────────────────────────────────
# W3 activity — /metrics: per-path request counts since the process started
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/metrics")
async def metrics():
    return {
        "endpoints": request_counts,
        "total": sum(request_counts.values()),
    }
