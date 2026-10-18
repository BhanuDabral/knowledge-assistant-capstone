"""tests/test_calibration.py — the fixed calibration helper (W5 take-home)."""
import sqlite3

from scripts.compute_calibration import compute_agreement, fetch_judge_scores, parse_my_scores

# The course sample's two tables (blind scores, then the judge's verdicts pasted below them).
SAMPLE = """# Judge Calibration
## My scores (filled in blind — without looking at the judge)
| Golden id | My accuracy | My groundedness | My format | One-line note |
|---|---|---|---|---|
| g001 | 4 | 4 | 4 | a |
| g003 | 3 | 3 | 4 | a |
| g005 | 4 | 4 | 3 | a |
| g007 | 4 | 3 | 4 | a |
| g009 | 3 | 4 | 4 | a |
| g011 | 2 | 3 | 4 | a |
| g015 | 4 | 4 | 3 | a |
| g016 | 3 | 3 | 4 | a |
| g019 | 4 | 4 | 4 | a |
| g020 | 2 | 2 | 3 | a |
## Judge's verdicts (revealed after my blind scoring)
| Golden id | Judge accuracy | Judge groundedness | Judge format |
|---|---|---|---|
| g001 | 4 | 4 | 4 |
| g005 | 4 | 4 | 4 |
| g011 | 4 | 3 | 4 |
| g015 | 4 | 3 | 3 |
"""
JUDGE = {"g001": (4, 4, 4), "g003": (3, 3, 4), "g005": (4, 4, 4), "g007": (4, 3, 4), "g009": (3, 4, 4),
         "g011": (4, 3, 4), "g015": (4, 3, 3), "g016": (3, 3, 4), "g019": (4, 4, 4), "g020": (2, 2, 3)}


def test_judge_table_in_the_same_file_does_not_overwrite_my_scores(tmp_path):
    p = tmp_path / "cal.md"
    p.write_text(SAMPLE, encoding="utf-8")
    mine, unfilled = parse_my_scores(p)
    assert mine["g011"]["accuracy"] == 2 and not unfilled            # the course script read 4 here


def test_course_sample_agreement_is_27_of_30(tmp_path):
    p = tmp_path / "cal.md"
    p.write_text(SAMPLE, encoding="utf-8")
    db = tmp_path / "a.db"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE eval_runs (golden_id, accuracy, groundedness, format, eval_run_label)")
        c.executemany("INSERT INTO eval_runs VALUES (?,?,?,?, 'eval-run-001')", [(k, *v) for k, v in JUDGE.items()])
    mine, _ = parse_my_scores(p)
    r = compute_agreement(mine, fetch_judge_scores(str(db), "eval-run-001", list(mine)))
    assert (r["exact"], r["within_1"], r["total"]) == (27, 29, 30)
    assert [(g, d) for g, d, *_ in r["disagreements_gt1"]] == [("g011", "accuracy")]


def test_unfilled_rows_are_reported(tmp_path):
    p = tmp_path / "cal.md"
    p.write_text("## My scores\n| g002 | _ | _ | _ | _ |\n| g003 | 3 | 3 | 3 | ok |\n", encoding="utf-8")
    mine, unfilled = parse_my_scores(p)
    assert list(mine) == ["g003"] and unfilled == ["g002"]


def test_real_sheet_is_fully_scored_and_findings_table_is_not_read_as_scores():
    mine, unfilled = parse_my_scores("docs/judge-calibration.md")
    assert len(mine) == 10 and not unfilled
    assert mine["g019"] == {"accuracy": 1, "groundedness": 1, "format": 4}    # not the "4 / 1" findings row
