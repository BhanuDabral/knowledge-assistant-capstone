# ADR 0002 — /v1/ask API Contract

**Status:** Locked from Week 3 · Extended Week 4 (schema versioning, cost budget, chosen model). Draft for owner review.
**Defended at:** Design Review #1 (Week 5).
**Owners:** Bhanu Dabral
**Date:** 2026-10-17 (W3) · 2026-10-17 (W4 extension)

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

**Response:** streamed `text/plain; charset=utf-8`. Since W4 the chunks are real LLM tokens as they are generated (W3 simulated them, 50 ms per word). Concatenating every chunk gives the full answer.

### Endpoint: `POST /ask_batched`

Same input contract as `/ask`. Returns the full `Answer` as JSON, without streaming. Used for testing and for callers that can't consume streams.

**Response body (`Answer`):**

| Field    | Type  | Required | Notes |
|----------|-------|:--------:|-------|
| content  | str   |   Yes    | The generated answer. |
| cost_usd | float |   Yes    | Cost of this call in USD, from `response.usage` × `cost.RATES` (W4; was a `0.0001` placeholder in W3). |
| retries  | int   |   Yes    | Retries that fired in this call: 0, 1 or 2 (up to 3 attempts, 1 s / 2 s backoff). |
| confidence | float |  No (default 1.0) | **W4, additive.** Model's self-reported confidence, 0.0–1.0. Not calibrated (see `docs/lab4-model-comparison.md`). |
| sources  | list[str] | No (default `[]`) | **W4, additive.** Sources the model says it used. Empty until retrieval lands (W6–W11). |
| schema_version | str | No (default `"v1"`) | **W4, additive.** Version of this body shape; see the schema versioning rule. |

**Internal note:** in W3 the endpoints translated between this contract and the W2 pipeline's models (`Question.text`; `Answer.text`). Since W4 the API and the LLM layer share `src/pipeline/models.py`, and `/ask_batched` uses tool-calling (`src/pipeline/llm.py`) to get the structured `Answer` directly. Each `/ask_batched` answer is also saved to `data/answers.db` with its model and cost (internal, not part of the contract).

### Endpoint: `GET /health`

Returns `{"status": "ok"}` with HTTP 200 when the service is alive.

### Error responses

- **`422 Unprocessable Entity`**: the request fails validation (missing field, wrong field name, wrong type, malformed JSON). The body follows FastAPI's default `{"detail": [...]}` shape. Verified for all four cases in `docs/wk3-stress-notes.md`.
- **`422` with `type: "too_many_tokens"`** (W4): the question is longer than `Settings.max_input_tokens` (2,000, counted with tiktoken before any LLM call). Same `{"detail": [...]}` shape, so the error-response shape is unchanged.
- **`5xx`**: the LLM provider still failing after the retry budget (3 attempts; `ask_llm_with_retry` in W3, the tool-calling `ask_llm` since W4). On `/ask`, an error raised after streaming has started cannot change the status code (already sent as 200); the stream is cut short instead.

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
- Schema versioning of the response body: see the next section (added W4). The endpoint contract is separate from the body schema.

## Schema versioning rule (added W4)

Every `Answer` carries a `schema_version` field. **Today's shape is `v1`.**

- It stays `v1` through any **additive** change: new optional fields with defaults, new endpoints at different paths, internal model swaps, prompt edits that keep the output shape, retry / logging / observability changes. W4 itself is exactly this: `confidence`, `sources` and `schema_version` were added with defaults, and the W3 fields are unchanged.
- **Breaking** changes ship as a new `schema_version` (`v2`, `v3`, …): removing a required field, renaming a public field, changing a field's type, making an optional field required, a semantic change (for example `cost_usd` meaning something other than USD), or changing the error-response shape.
- When `v2` ships, `/ask` and `/ask_batched` still return `v1` by default; a header `X-Schema-Version: v2` (or `?schema_version=v2`) opts in. Both run in parallel for at least two weeks, and the retirement date is announced here first.

## Cost budget (added W4)

Capstone `/ask_batched` calls must cost **≤ $0.01 each on average** over a representative batch. It is a soft budget: the intent is to fail loudly in observability if the average suddenly jumps, not to reject individual calls.

Measured in Lab Step 3 (`scripts/compare_models.py`, real `response.usage`):

| Set | gpt-4o-mini avg / answer | gpt-4o avg / answer |
|---|---|---|
| 10 lab questions | $0.000072 | $0.001479 |
| 20 capstone questions | $0.000094 | $0.001723 |

Both models are well under budget; gpt-4o-mini uses about 1% of it. The budget stays at $0.01 until retrieval (W6+) adds context tokens; re-measure then.

## Chosen default model (added W4)

The default `Settings.model` is **`gpt-4o-mini`**. In the comparison it was 18–20× cheaper than `gpt-4o` and close in quality on general questions. On the 7 source-checked capstone questions `gpt-4o` scored better (3 correct, 3 partial, 1 wrong, against 2 / 2 / 3), but it was still wrong or vague on regulator-specific details. The gap that matters for this capstone is grounding, which retrieval addresses, not model size. `gpt-4o` remains available through the same code path (`Settings(model="gpt-4o")`) for harder synthesis questions.

## The W3 contract held through W4

No field was removed, renamed or retyped; `/ask`, `/ask_batched` and `/health` keep their paths and inputs. The new fields have defaults, so a W3-shaped `Answer(content=…, cost_usd=…, retries=…)` still validates (`tests/test_pipeline_w4.py::TestAnswerBackwardCompatibility`), and all W3 tests still pass.

## Consequences

- **Positive.** The Streamlit UI, the W5 eval harness and any later consumer integrate once. W4 → W30 internal changes (retrieval over the IMDA/PDPC/MAS corpus, citations, confidence) happen behind the contract, as additive optional fields.
- **Negative.** We commit to maintaining v1 even when its internals become legacy. Acceptable cost.
- **Open.** Authentication is out of scope for v1. When it arrives in W28/W29 it will require an `Authorization` header but won't change the request or response shape.

### Open items found while writing this ADR (all resolved 2026-10-17)

1. ~~**Empty questions are accepted.**~~ **Resolved 2026-10-17:** `Question.question` now has `min_length=1`, so an empty question gets 422 before any LLM call (test: `test_ask_rejects_empty_question`). Remaining edge: a whitespace-only question (`"   "`) is still accepted, because spaces count towards the length.
2. ~~**No retries on the API path.**~~ **Resolved 2026-10-17:** both endpoints now retry (W3: `ask_llm_with_retry`; W4: `/ask_batched` via the tool-calling `ask_llm`; a stream is not retried part-way) (3 attempts, 1 s / 2 s backoff), so a transient provider error is retried and `retries` reports how many fired (test: `test_ask_batched_retries_transient_failure`). A retry-policy change: no version bump. Note: this deviates from the course reference `api/main.py`, which calls `ask_llm`.
3. ~~**No `/v1` prefix.**~~ **Decided 2026-10-17: no prefix.** The routes stay `/ask`, `/ask_batched` and `/health`. The course UI, tests and stress script all call these paths, and "v1" names the contract version, not a URL segment. If a breaking change ever needs v2, it ships as `/v2/ask` alongside the unprefixed v1 routes.

## Tests securing this contract

- `tests/test_api.py::test_ask_rejects_missing_question`: the validation contract (422 on a missing `question`).
- `tests/test_api.py::test_ask_rejects_empty_question`: 422 on an empty `question` (`min_length=1`).
- `tests/test_api.py::test_ask_batched_retries_transient_failure`: one transient failure is retried; 200 with `retries: 1`.
- `tests/test_api.py::test_health_returns_ok`: the `/health` contract.
- `tests/test_pipeline.py::test_ask_llm_calls_fake_once` and `::test_retry_three_times_on_failure`: the pipeline call shape and retry budget behind the endpoints.
- `tests/test_pipeline_w4.py` (course, 10 tests): W3-shaped `Answer` still constructs; new-field defaults; `schema_version` defaults to `v1`; tool schema shape.
- `tests/test_cost.py` (course, 9 tests): the cost formula and `RATES` table.
- `tests/test_w4_capstone.py` (7 tests): tiktoken guard (422 `too_many_tokens`, no LLM call); real-path parsing and cost from `usage` (mocked client); streaming; answers saved with honest model labels.
- *(Not yet)* `tests/test_contract.py`: snapshot-test `/openapi.json` to catch accidental contract breakage in CI.

> W4 extension drafted by Claude Code from the measured results (Lab Step 3) and the course template `adr_0002_extended.md`. Review the budget and model choice before relying on them.

