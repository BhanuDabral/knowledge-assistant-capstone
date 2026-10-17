# Week 3 Activity — `/metrics` endpoint

**Added to `api/main.py`:**
- `request_counts: dict[str, int]`: a module-level counter, path → count (in memory).
- `count_requests`: an `@app.middleware("http")` function that increments the counter for every request, then `await call_next(request)`.
- `GET /metrics`: returns `{"endpoints": request_counts, "total": sum(...)}`.

## Run (2026-10-17, uvicorn `--reload` on port 8000, real OpenAI API)

The reload after saving `api/main.py` reset the counter, which is the "restart" step. Then:

```bash
curl http://localhost:8000/health        # ×3
curl -X POST http://localhost:8000/ask_batched -H "Content-Type: application/json" -d '{"question": "What is RAG?"}'
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question": "Explain async in two sentences."}'
curl http://localhost:8000/metrics
```

```json
{
    "endpoints": {
        "/health": 3,
        "/ask_batched": 1,
        "/ask": 1,
        "/metrics": 1
    },
    "total": 6
}
```

Exactly the expected result. `/metrics` counted the request that fetched it.

**Extra observation.** Opening `/metrics` in Chrome afterwards changed the counts to `"/metrics": 3, "/favicon.ico": 1, "total": 9`. The browser requested `/favicon.ico` on its own, a path this API does not serve (404), and the middleware counted it anyway: it records every path, valid or not.

## What I observed

What happens after a restart: All request counts are lost because request_counts is stored in memory. Every restart, including --reload, resets the counters to zero. In real systems, tools like Prometheus are used to collect and retain metrics so we can track them over time.

Handling simultaneous requests: Two /health requests may not always increase the counter by 2. Both could read the same value and update it, causing one count to be missed. This is unlikely in our single-process setup, but multiple workers would maintain separate counters. Real systems use atomic counters, locks or Redis INCR to ensure accurate counting.

