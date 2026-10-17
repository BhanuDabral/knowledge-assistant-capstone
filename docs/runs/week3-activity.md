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

- **What's lost if the process restarts:** everything. `request_counts` lives in the process's memory, so a restart (including every `--reload` while editing) sets all counts back to zero. A real metrics system keeps the values outside the process (scraped or pushed to a durable store such as Prometheus), so history survives restarts and can be compared over time.
- **Would two simultaneous `/health` requests always take the counter from N to N+2?** Not guaranteed. The read (`.get(path, 0)`), add and write are separate steps, so two requests interleaved between them could both read N and both write N+1, losing one count. In this single-process uvicorn it is unlikely, because there is no `await` between the read and the write, but with several worker processes each one keeps its own separate dict. Real systems use atomic counters (a lock, or Redis `INCR`).

> Note: drafted by Claude Code from the actual run output above. Review and reword these observations in your own words before submitting.
