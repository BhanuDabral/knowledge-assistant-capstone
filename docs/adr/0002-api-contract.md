# ADR 0002 — /v1/ask API Contract

**Status:** Locked from Week 3 (Draft v1 — for owner review).
**Defended at:** Design Review #1 (Week 5).
**Owners:** Bhanu Dabral
**Date:** 2026-10-17

## Context

The capstone is a **Singapore AI & Data Governance Assistant**: a Q&A service over IMDA, PDPC and MAS frameworks (the 15-document corpus in `data/corpus/SOURCES.md`), for practitioners who need quick, sourced answers on topics such as FEAT, the PDPA and the Model AI Governance Frameworks.

By the end of W3 it has a FastAPI service (`api/main.py`) in front of the W2 async pipeline. Every later week changes the answer-generation core: different models in W4, retrieval over the corpus in W6–W11, reranking in W7+, agents in W19+. The service's HTTP surface must stay stable so that its callers don't have to rewrite their integration each week. Today the callers are the Streamlit UI (`ui/app.py`); later they include the W5 evaluation harness and production consumers.

This ADR locks the v1 API contract for `/ask`, `/ask_batched` and `/health`. "v1" is the contract version; the routes are currently served **without** a `/v1` path prefix (`POST /ask`, not `POST /v1/ask`).

## Decision

### Endpoint: `POST /ask`

**Request body (`Question`):**

| Field    | Type | Required | Notes |
|----------|------|:--------:|-------|
| question | str  |   Yes    | Free text, minimum length 1 (`Field(min_length=1)`). `""` → 422. |

**Response:** streamed `text/plain; charset=utf-8`. Words arrive one at a time, 50 ms apart in W3. Concatenating every chunk gives the full answer.

### Endpoint: `POST /ask_batched`

Same input contract as `/ask`. Returns the full `Answer` as JSON, without streaming. Used for testing and for callers that can't consume streams.

**Response body (`Answer`):**

| Field    | Type  | Required | Notes |
|----------|-------|:--------:|-------|
| content  | str   |   Yes    | The generated answer. |
| cost_usd | float |   Yes    | Cost of this call. Placeholder (`0.0001`) in W3; real from `response.usage` in W4. |
| retries  | int   |   Yes    | Retries that fired in this call: 0, 1 or 2 (up to 3 attempts, 1 s / 2 s backoff). |

**Internal note:** the W2 pipeline behind these endpoints uses different field names (`Question.text`; `Answer.question`/`text`). The translation between the public contract and the internal models happens inside each endpoint handler in `api/main.py`. This separation is intentional: the internal models can change in W4+ without breaking the contract.

### Endpoint: `GET /health`

Returns `{"status": "ok"}` with HTTP 200 when the service is alive.

### Error responses

- **`422 Unprocessable Entity`**: the request fails validation (missing field, wrong field name, wrong type, malformed JSON). The body follows FastAPI's default `{"detail": [...]}` shape. Verified for all four cases in `docs/wk3-stress-notes.md`.
- **`5xx`**: the LLM provider still failing after the retry budget (3 attempts via `ask_llm_with_retry`). On `/ask`, an error raised after streaming has started cannot change the status code (already sent as 200); the stream is cut short instead.

### Not part of this contract

`GET /metrics` (the W3 activity's request counter) is internal observability, not a public contract. It is excluded here per the "don't bump for" list below, and needs its own ADR if an external consumer ever depends on it.

## Versioning Rule

- The v1 contract is locked from Week 3.
- **Don't bump** for additive changes:
  - New optional fields on `Answer`
  - Internal model swaps (including changes to the W2 pipeline's `text`-named fields)
  - Logging and observability changes (including `/metrics`)
  - Retry-policy tweaks
  - Internal prompt edits
- **Do bump to v2** (`/v2/ask`) for breaking changes:
  - Removing or renaming a field on the *public* shape (`Question`, `Answer`)
  - Changing a public field's type
  - Changing a field between required and optional
  - Changing what a field means
  - Changing the error-response shape
- When v2 ships, v1 runs in parallel for **at least 2 weeks** before retirement, and consumers get an `X-Deprecation` warning header.
- Schema versioning of the response body lands in W4 (a `schema_version` field on `Answer`). The endpoint contract is separate from the body schema.

## Consequences

- **Positive.** The Streamlit UI, the W5 eval harness and any later consumer integrate once. W4 → W30 internal changes (retrieval over the IMDA/PDPC/MAS corpus, citations, confidence) happen behind the contract, as additive optional fields.
- **Negative.** We commit to maintaining v1 even when its internals become legacy. Acceptable cost.
- **Open.** Authentication is out of scope for v1. When it arrives in W28/W29 it will require an `Authorization` header but won't change the request or response shape.

### Open items found while writing this ADR (all resolved 2026-10-17)

1. ~~**Empty questions are accepted.**~~ **Resolved 2026-10-17:** `Question.question` now has `min_length=1`, so an empty question gets 422 before any LLM call (test: `test_ask_rejects_empty_question`). Remaining edge: a whitespace-only question (`"   "`) is still accepted, because spaces count towards the length.
2. ~~**No retries on the API path.**~~ **Resolved 2026-10-17:** both endpoints now call `ask_llm_with_retry` (3 attempts, 1 s / 2 s backoff), so a transient provider error is retried and `retries` reports how many fired (test: `test_ask_batched_retries_transient_failure`). A retry-policy change: no version bump. Note: this deviates from the course reference `api/main.py`, which calls `ask_llm`.
3. ~~**No `/v1` prefix.**~~ **Decided 2026-10-17: no prefix.** The routes stay `/ask`, `/ask_batched` and `/health`. The course UI, tests and stress script all call these paths, and "v1" names the contract version, not a URL segment. If a breaking change ever needs v2, it ships as `/v2/ask` alongside the unprefixed v1 routes.

## Tests securing this contract

- `tests/test_api.py::test_ask_rejects_missing_question`: the validation contract (422 on a missing `question`).
- `tests/test_api.py::test_ask_rejects_empty_question`: 422 on an empty `question` (`min_length=1`).
- `tests/test_api.py::test_ask_batched_retries_transient_failure`: one transient failure is retried; 200 with `retries: 1`.
- `tests/test_api.py::test_health_returns_ok`: the `/health` contract.
- `tests/test_pipeline.py::test_ask_llm_calls_fake_once` and `::test_retry_three_times_on_failure`: the pipeline call shape and retry budget behind the endpoints.
- *(In W4)* `tests/test_contract.py`: snapshot-test `/openapi.json` to catch accidental contract breakage in CI.

> Drafted by Claude Code from the course template, the actual `api/main.py` and the W3 test results. Review the decisions and open items before relying on it.
