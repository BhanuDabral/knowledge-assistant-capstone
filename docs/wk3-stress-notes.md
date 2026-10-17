# Week 3 — Stress-test findings

**Service:** `uvicorn api.main:app --port 8000` (no `--reload`), real OpenAI API (`gpt-4o-mini`), macOS, Python 3.12, 2026-10-17. Server log captured for every test.

## Finding 1 — Malformed JSON (Lab 3a)

| Case | Request body | Status | Error detail |
|---|---|---|---|
| 1 Empty body | `{}` | **422** | `missing` — `body.question`: "Field required" |
| 2 Wrong field name | `{"q": "…"}` | **422** | `missing` — `body.question`: "Field required" |
| 3 Wrong type | `{"question": 42}` | **422** | `string_type` — "Input should be a valid string" |
| 4 Malformed JSON | `{"question": "…"` (no `}`) | **422** | `json_invalid` — "JSON decode error: Expecting ',' delimiter" |

None reached the application code: the server log shows only uvicorn's access line for each request and no `ask question=…` line from the endpoint, and no LLM call was made. Pydantic validation rejected all four for free. Case 4 returned 422 rather than 400; the guide allows either.

## Finding 2 — 5,000-character question (Lab 3b)

- A 5,146-character question to `/ask` returned **HTTP 200** and streamed a complete answer in **11.4 s** wall time.
- **No token-limit error.** The OpenAI call itself returned after about 3 s (per the server log); the other ~8 s is the simulated 50 ms-per-word streaming delay.
- Streaming worked as normal. The answer was generic rather than the PDPA's four actual conditions, the same retrieval gap seen in the W2 baseline.

## Finding 3 — Disconnect mid-stream (Lab 3c)

- **A — guide's test, `curl --max-time 1`:** curl exited with code 28 (timed out) before any word arrived, because the LLM takes about 3 s. The server logged the request but **no OpenAI response and no `asked:` line**: the abandoned request was cancelled before the LLM call completed. It did not "keep generating" as the guide describes.
- **B — true mid-stream disconnect** (read 15 words, then close the connection): the LLM call had completed and words were streaming; the server stopped writing when the client went away.
- **Both:** 0 tracebacks or errors in the server log, and `/health` returned `{"status":"ok"}` (200) afterwards.
- Note: uvicorn's access log records `200 OK` for both, because the status is sent before the body streams. The access log alone does not show a request was abandoned.

## Finding 4 — 50 parallel requests (Lab 3d)

`python scripts/stress_test.py --requests 50 --concurrent 10`

| Metric | Result | Guide's example |
|---|---|---|
| Successes | **50 / 50** | 50 / 50 |
| Total wall time | 100.49 s | 72.14 s |
| Effective req/s | 0.50 | 0.69 |
| Latency min / p50 / p95 / max | 2.28 / **14.86** / **37.00** / 38.59 s | 5.12 / 6.81 / 9.42 / 10.71 s |

- **No errors:** all 52 OpenAI responses in the session log are `200 OK`; 0 rate-limit (429) responses; 0 retries; 0 tracebacks.
- **Why the latency is high:** each response is drip-fed at 50 ms per word (W3's simulated streaming), and these answers are long (about 250 words, roughly 12–15 s of artificial delay each). On top of that, with 10 requests in flight, OpenAI's responses were spread over about 72 s. The max (38.6 s) is within the script's 60 s timeout, but not by much.
- **Concurrency is not the main driver.** The end-of-week replay (`--requests 10 --concurrent 3`) gave 10/10, p50 **16.40 s**, p95 **35.79 s**, about the same as at 10 concurrent. Latency is set mostly by answer length times the 50 ms-per-word streaming delay, not by load.
- **SQLite did not capture the requests.** The guide's check `SELECT COUNT(*) FROM answers WHERE created_at > …` fails with **"no such column: created_at"** (this schema's column is `ts`). The corrected check found **0** new rows: the `answers` table held 248 rows before and after. The `/ask` path calls `ask_llm` only; it never writes to SQLite. Only the batch CLI (`python -m src.pipeline.pipeline`) persists.

## Known limits / follow-ups

- **No persistence for API traffic.** `/ask` and `/ask_batched` don't write to `results.db`. Decide in W4–W6 whether API calls should be logged to SQLite, and fix the guide's `created_at` check against this schema.
- **Simulated streaming dominates latency.** 50 ms per word adds about 13 s to a 270-word answer. W4's real LLM-side streaming should remove this, so re-measure p50 and p95 then.
- **No length limit on questions.** 5,000 characters worked, but there is no `max_length` on `Question.question`, and much larger inputs will eventually hit the model's context limit (W7).
- **Cost tracking is a placeholder** (`cost_usd = 0.0001` per call). Real cost from `response.usage` comes in W4.
- **Answers are ungrounded.** The model invented three different expansions of "SAFR" during these tests (it is *Safeguards for Agentic Finance at Runtime*). Retrieval over the corpus (W11) is the fix.
- **No timeout or cancellation telemetry.** Abandoned requests are invisible in the access log; observability lands in W22.


