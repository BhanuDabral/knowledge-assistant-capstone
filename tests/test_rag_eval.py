"""tests/test_rag_eval.py — W6 eval measures, KPI maths and the runner. Offline (judges mocked)."""
import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from scripts import compute_kpis, run_rag_eval
from src.eval import rag_metrics as m
from src.pipeline.answer_store import connect, save_rag_run

EXPECTED = {"sources": [{"doc": "A.pdf", "pages": [5, 6]}]}


def _hit(source, start, end):
    return {"source": source, "page_start": start, "page_end": end}


def test_retrieval_hit_doc_and_page():
    assert m.retrieval_hit([_hit("A.pdf", 6, 7)], EXPECTED) == (True, True)
    assert m.retrieval_hit([_hit("A.pdf", 9, 9)], EXPECTED) == (True, False)    # right doc, wrong page
    assert m.retrieval_hit([_hit("B.pdf", 5, 5)], EXPECTED) == (False, False)
    assert m.retrieval_hit([], {"out_of_scope": True, "sources": []}) == (None, None)


def test_oracle_hits_are_the_cited_pages(tmp_path):
    (tmp_path / "A.txt").write_text("only page")
    hits = m.oracle_hits({"sources": [{"doc": "A.txt", "pages": [1]}]}, tmp_path)
    assert hits[0]["chunk_id"] == "a:p1:oracle" and hits[0]["text"] == "only page"


def test_nearest_rank():
    assert m.nearest_rank([3.0, 1.0, 2.0], 50) == 2.0 and m.nearest_rank([], 95) is None


def _fake_client(payload: dict):
    resp = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=100, completion_tokens=10),
                           choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=resp))))
    return client


@pytest.mark.asyncio
async def test_refusal_and_support_judges_parse_json():
    declined, cost = await m.classify_refusal("q", "I don't know.", client=_fake_client({"declined": True}))
    assert declined is True and cost > 0
    detail, _ = await m.judge_citation_support("q", "[x] text", "a", client=_fake_client(
        {"support": "partial", "unsupported_claims": ["c"], "reasoning": "one claim missing"}))
    assert detail["support"] == "partial"
    with pytest.raises(ValueError):
        await m.judge_citation_support("q", "p", "a", client=_fake_client({"support": "maybe"}))


def _seed(db, label):
    rows = [("g001", 1, 1, 0, "full", 2.0), ("g002", 0, 0, 0, "none", 4.0), ("g019", None, None, 1, None, 1.0)]
    with connect(db) as conn:
        for gid, hd, hp, dec, sup, lat in rows:
            save_rag_run(conn, label=label, golden_id=gid, condition="rag", chunk_size=500, chunk_overlap=50,
                         question="q", answer="a", hit_doc=hd, hit_page=hp, declined=dec, support=sup,
                         latency_s=lat, candidate_cost_usd=0.0003)


def test_kpis_from_rows(tmp_path):
    db = tmp_path / "a.db"
    _seed(db, "L")
    sources = {"g001": EXPECTED, "g002": EXPECTED, "g019": {"out_of_scope": True, "sources": []}}
    with sqlite3.connect(db) as conn:
        k = compute_kpis.kpis(conn, "L", sources, tmp_path / "none.csv")
    assert k["retrieval_hit_rate"] == "1 / 2" and k["correct_refusals"] == "1 / 1"
    assert k["unnecessary_refusals"] == "0 / 2" and k["grounded_rate"].startswith("1 / 2")
    assert k["latency_p95"] == "4.00s" and k["cost_per_query"] == "$0.000300"
    assert k["task_success"] == "pending" and k["accuracy"] == "not judged"


def test_task_success_reads_grades(tmp_path):
    f = tmp_path / "g.csv"
    f.write_text("label,golden_id,grade\nL,g001,Y\nL,g002,Partial\nL,g003,N\nX,g001,Y\n")
    assert compute_kpis.task_success(f, "L") == "1 Y + 1 Partial / 3"


@pytest.mark.asyncio
async def test_runner_none_condition_records_rows(tmp_path):
    db = tmp_path / "a.db"
    args = run_rag_eval.parse_args(["--label", "T", "--condition", "none", "--no-judge", "--db", str(db)])
    with patch.object(run_rag_eval, "classify_refusal", AsyncMock(return_value=(False, 0.0))):
        assert await run_rag_eval.run(args) == 0                     # fake LLM via PIPELINE_USE_FAKE
    n, cond = sqlite3.connect(db).execute("SELECT COUNT(*), MIN(condition) FROM rag_runs WHERE label='T'").fetchone()
    assert (n, cond) == (20, "none")
    assert await run_rag_eval.run(args) == 1                         # same label twice is refused


def test_cited_in_text_keeps_only_retrieved_ids():
    from src.rag.naive_rag import cited_in_text
    hits = [{"chunk_id": "a:p1:c0"}, {"chunk_id": "b:p2:c3"}]
    text = "Fact one [a:p1:c0]. Fact two [made-up:p9:c9]. Again [a:p1:c0] and [b:p2:c3]."
    assert cited_in_text(text, hits) == ["a:p1:c0", "b:p2:c3"]


@pytest.mark.asyncio
async def test_runner_rag_stream_condition_uses_the_stream_path(tmp_path):
    from src.pipeline.settings import Settings
    from src.rag import naive_rag as rag
    (tmp_path / "corpus").mkdir()
    (tmp_path / "corpus" / "feat.txt").write_text("FEAT means fairness ethics accountability transparency. " * 10)
    index = await rag.build_index(tmp_path / "corpus", Settings(use_fake=True), size=120, overlap=20)
    rag.save_index(index, tmp_path / "idx")
    db = tmp_path / "a.db"
    args = run_rag_eval.parse_args(["--label", "S", "--condition", "rag-stream", "--index", str(tmp_path / "idx"),
                                    "--no-judge", "--no-support", "--db", str(db)])
    with patch.object(run_rag_eval, "classify_refusal", AsyncMock(return_value=(False, 0.0))):
        assert await run_rag_eval.run(args) == 0
    rows = sqlite3.connect(db).execute("SELECT condition, answer, hit_doc, retrieved_json FROM rag_runs WHERE label='S'").fetchall()
    assert len(rows) == 20 and rows[0][0] == "rag-stream" and rows[0][1].startswith("[FAKE]")
    assert rows[0][2] == 0 and json.loads(rows[0][3])                # retrieval ran and was scored

