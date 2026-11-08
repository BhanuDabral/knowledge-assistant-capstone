"""tests/test_stress_test.py — percentile maths and saved report of the stress test. Offline."""
import argparse
import json

import httpx
import pytest

from scripts import stress_test


def test_nearest_rank_matches_definition():
    values = [float(v) for v in range(1, 11)]                 # 1..10
    assert stress_test.nearest_rank(values, 50) == 5.0
    assert stress_test.nearest_rank(values, 95) == 10.0       # n = 10: p95 is the max
    forty = [float(v) for v in range(1, 41)]
    assert stress_test.nearest_rank(forty, 95) == 38.0        # n = 40: ceil(38) -> 38th value


def test_summary_ignores_failed_requests():
    results = [{"status": 200, "elapsed_s": 2.0}, {"status": 200, "elapsed_s": 1.0}, {"status": "ERR", "elapsed_s": 60.0}]
    s = stress_test.summarise(results, total_s=4.0)
    assert (s["successes"], s["failures"], s["min_s"], s["max_s"]) == (2, 1, 1.0, 2.0)


def test_load_questions_reads_the_golden_set():
    qs = stress_test.load_questions(stress_test.ROOT / "data/golden_set.jsonl")
    assert len(qs) == 20 and all(isinstance(q, str) and q for q in qs)


@pytest.mark.asyncio
async def test_run_saves_config_and_every_request(tmp_path, monkeypatch):
    def handler(request):
        return httpx.Response(200, text="answer")
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient
    monkeypatch.setattr(stress_test.httpx, "AsyncClient", lambda: real_client(transport=transport))
    out = tmp_path / "run.json"
    args = argparse.Namespace(requests=5, concurrent=2, questions=str(stress_test.ROOT / "data/golden_set.jsonl"),
                              api_url="http://test", timeout=5.0, output=str(out))
    await stress_test.run(args)
    saved = json.loads(out.read_text())
    assert saved["summary"]["successes"] == 5 and len(saved["requests"]) == 5
    assert saved["config"]["concurrent"] == 2 and saved["config"]["endpoint"] == "http://test/ask"
    assert "server_system_prompt_file" in saved["config"]
