"""tests/test_golden.py — the golden-set loader and validator (W5 Step 2)."""
import json

import pytest

from src.eval.golden import bucket_of, get_entry, load_golden, validate_golden_set


def _write(tmp_path, rows):
    p = tmp_path / "g.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n\n", encoding="utf-8")
    return p


ROW = {"id": "g001", "question": "Q?", "ideal_answer": "A.", "notes": "happy-path. x"}


def test_real_golden_set_is_14_4_2():
    r = validate_golden_set("data/golden_set.jsonl")
    assert r["n"] == 20 and r["coverage"] == {"happy": 14, "harder": 4, "edge": 2}
    assert r["ids"] == [f"g{i:03d}" for i in range(1, 21)]


def test_every_real_entry_cites_a_source():
    assert all(e.source for e in load_golden("data/golden_set.jsonl"))


@pytest.mark.parametrize("notes, bucket", [
    ("happy-path. Source: x", "happy"), ("harder · multi-hop.", "harder"),
    ("Harder. caps ok", "harder"), ("edge. not in docs", "edge"),
])
def test_bucket_reads_first_word(notes, bucket):
    assert bucket_of(notes) == bucket


def test_unknown_bucket_is_rejected(tmp_path):
    p = _write(tmp_path, [dict(ROW, notes="easy. wrong bucket")])
    with pytest.raises(ValueError, match=":1:"):
        load_golden(p)


def test_empty_question_is_rejected_with_line_number(tmp_path):
    p = _write(tmp_path, [ROW, dict(ROW, id="g002", question="")])
    with pytest.raises(ValueError, match=":2:"):
        load_golden(p)


def test_duplicate_ids_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="duplicate"):
        validate_golden_set(_write(tmp_path, [ROW, ROW]))


def test_blank_lines_skipped_and_get_entry(tmp_path):
    p = _write(tmp_path, [ROW, dict(ROW, id="g002", notes="edge. x")])
    assert get_entry(p, "g002").bucket == "edge"
    with pytest.raises(KeyError):
        get_entry(p, "g999")
