"""scripts/compute_calibration.py — W5 take-home: agreement between your blind scores and the judge.

Based on the course's compute_calibration.py (W5_Practice_Assignment_Solution_Activity), with a
capstone fix: the course version matched EVERY "| g001 | 4 | 4 | 4 |" row in the file, so once the
judge's verdict table was pasted into the same markdown (as the activity tells you to), the judge's
rows overwrote yours and agreement came out at 100%. On the course's own sample it reports 30/30;
the sample's real agreement is 27/30. Here only rows inside the "## My scores" section are read,
unfilled rows ("_") are reported instead of silently skipped, and the judge's scores always come
from the eval_runs table.

Usage:
    python scripts/compute_calibration.py --calibration-file docs/judge-calibration.md \\
        --db data/answers.db --label eval-run-001
"""
from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

DIMS = ("accuracy", "groundedness", "format")
ROW = re.compile(r"^\|\s*(g\d{3})\s*\|\s*([1-4])\s*\|\s*([1-4])\s*\|\s*([1-4])\s*\|")
ANY_ID_ROW = re.compile(r"^\|\s*(g\d{3})\s*\|")


def parse_my_scores(path: str | Path) -> tuple[dict, list[str]]:
    """Scores from the '## My scores' section only. Returns (scores, ids still unfilled)."""
    scores, unfilled, inside = {}, [], False
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = line.lower().startswith("## my scores")
            continue
        if not inside:
            continue
        m = ROW.match(line)
        if m:
            gid, *vals = m.groups()
            scores[gid] = dict(zip(DIMS, map(int, vals)))
        elif (m2 := ANY_ID_ROW.match(line)):
            unfilled.append(m2.group(1))
    return scores, unfilled


def fetch_judge_scores(db: str, label: str, ids: list[str]) -> dict:
    with sqlite3.connect(db) as conn:
        q = (f"SELECT golden_id, accuracy, groundedness, format FROM eval_runs "
             f"WHERE eval_run_label = ? AND golden_id IN ({','.join('?' * len(ids))})")
        return {g: dict(zip(DIMS, (a, gr, f))) for g, a, gr, f in conn.execute(q, (label, *ids))}


def compute_agreement(mine: dict, judge: dict) -> dict:
    exact = within1 = total = 0
    per_dim = {d: [0, 0] for d in DIMS}                       # [exact, total]
    big = []
    for gid, my in mine.items():
        if gid not in judge:
            continue
        for d in DIMS:
            delta = abs(my[d] - judge[gid][d])
            total += 1
            per_dim[d][1] += 1
            exact += delta == 0
            per_dim[d][0] += delta == 0
            within1 += delta <= 1
            if delta > 1:
                big.append((gid, d, my[d], judge[gid][d], delta))
    return {"exact": exact, "within_1": within1, "total": total, "per_dim": per_dim, "disagreements_gt1": big}


def print_summary(r: dict) -> None:
    t = r["total"]
    print("\nCalibration summary")
    print("-------------------")
    print(f"  n entries           : {t // 3}")
    print(f"  n dimension-scores  : {t}")
    print(f"  exact agreement     : {r['exact']} / {t}  ({100 * r['exact'] / t:.0f}%)")
    print(f"  within-1 agreement  : {r['within_1']} / {t}  ({100 * r['within_1'] / t:.0f}%)")
    print("  per-dimension exact :")
    for d, (e, n) in r["per_dim"].items():
        print(f"    {d:<16}  : {e} / {n}")
    print(f"  disagreements > 1   : {len(r['disagreements_gt1'])}")
    for gid, d, mine, judge, delta in r["disagreements_gt1"]:
        who = "I rated higher" if mine > judge else "judge rated higher"
        print(f"    {gid}: I scored {d[0]}={mine} / judge={judge} (Δ={delta}). {who}.")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Judge calibration agreement (W5 take-home)")
    p.add_argument("--calibration-file", required=True)
    p.add_argument("--db", required=True)
    p.add_argument("--label", required=True)
    a = p.parse_args(argv)
    mine, unfilled = parse_my_scores(a.calibration_file)
    if unfilled:
        print(f"Not scored yet: {', '.join(unfilled)} — fill every row of '## My scores' with 1-4 first.")
    if not mine:
        print("No completed rows found under '## My scores'.")
        return 1
    judge = fetch_judge_scores(a.db, a.label, list(mine))
    if not judge:
        print(f"No judge scores in {a.db} for label {a.label!r}.")
        return 1
    print_summary(compute_agreement(mine, judge))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
