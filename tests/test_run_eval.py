"""tests/test_run_eval.py — re-judge mode re-scores stored answers without calling the app. Offline."""
import argparse
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

from scripts import run_eval
from src.eval.judge import JudgeScore
from src.pipeline.answer_store import connect, save_eval_run


@pytest.mark.asyncio
async def test_rejudge_copies_stored_answers_under_a_new_label(tmp_path):
    db = tmp_path / "a.db"
    with connect(db) as conn:
        for gid in ("g001", "g002"):
            save_eval_run(conn, golden_id=gid, question=f"Q {gid}", candidate_answer=f"ANSWER {gid}",
                          ideal_answer=f"IDEAL {gid}", candidate_model="gpt-4o-mini", judge_model="gpt-4o",
                          accuracy=1, groundedness=1, format=1, reasoning="old verdict", eval_run_label="old")
    judge = AsyncMock(return_value=JudgeScore(accuracy=3, groundedness=3, format=4, reasoning="new verdict here"))
    args = argparse.Namespace(golden_set="data/golden_set.jsonl", db=str(db), label="new", rejudge="old",
                              judge_model="gpt-4o", api_url="http://unused", candidate_model="x")
    with patch.object(run_eval, "judge_one", judge), patch.object(run_eval.httpx, "AsyncClient") as http:
        assert await run_eval.run(args) == 0
    http.assert_not_called()                                         # the app is never asked again
    assert [c.args for c in judge.call_args_list] == [("Q g001", "IDEAL g001", "ANSWER g001"),
                                                      ("Q g002", "IDEAL g002", "ANSWER g002")]
    rows = sqlite3.connect(db).execute(
        "SELECT golden_id, candidate_answer, format FROM eval_runs WHERE eval_run_label='new' ORDER BY golden_id").fetchall()
    assert rows == [("g001", "ANSWER g001", 4), ("g002", "ANSWER g002", 4)]
