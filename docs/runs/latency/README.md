# Latency runs (KPI 3)

Each file here is one run of `scripts/stress_test.py`: the configuration, every request's raw
timing and status, and the summary. p95 is nearest-rank (the ceil(0.95 × n)-th fastest request),
so re-computing it from `requests` gives the same number.

| File | Date | Requests × concurrent | Questions | min / p50 / p95 / max (s) |
|---|---|---|---|---|
| `stress-2026-11-08-40x3.json` | 08/11/2026 | 40 × 3 | golden set (20) | 1.15 / 2.09 / **4.22** / 4.62 |

Reproduce (API running: `uvicorn api.main:app --port 8000`, same `.env`):

```bash
python scripts/stress_test.py --requests 40 --concurrent 3
```

## Earlier figure, not reproducible

The M1 documents quoted **p95 8.55 s** (W4). That run printed its numbers to the terminal only;
no raw results were kept. It used 10 requests at 3 concurrent, so its "p95" was simply the slowest
request, and it asked the course's HR-policy placeholder questions, not the capstone's. It is
superseded by the run above (DR #1 feedback: retain raw latency results and configuration).
