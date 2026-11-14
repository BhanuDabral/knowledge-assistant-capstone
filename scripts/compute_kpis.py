"""scripts/compute_kpis.py — KPIs for one or more RAG eval labels (W6 snapshot).

Reads rag_runs (+ eval_runs for the judge's accuracy) from data/answers.db.

  retrieval_hit_rate   document in top-K, over answerable entries (course KPI); page_hit_rate is stricter
  grounded_rate        DR #1 "citation support": answers fully supported by their passages,
                       over answers that had passages and didn't decline
  correct_refusals     declined, over out-of-scope entries (g019, g020)
  unnecessary_refusals declined, over answerable entries
  cost_per_query       candidate cost (chat + query embedding), mean
  latency_p50 / p95    seconds per question, nearest-rank
  accuracy             W5 judge (rubric v2), mean 1-4, when the label was judged
  task_success         your eyeball grades (docs/kpi/wk6-task-success.csv), when present

Usage:
    python scripts/compute_kpis.py --label wk6-rag-medium --label wk6-oracle
    python scripts/compute_kpis.py --label wk6-rag-small --metric retrieval_hit_rate --plain
"""
import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.eval.rag_metrics import load_golden_sources, nearest_rank

METRICS = ("retrieval_hit_rate", "page_hit_rate", "grounded_rate", "correct_refusals", "unnecessary_refusals",
           "cost_per_query", "latency_p50", "latency_p95", "accuracy", "task_success")


def _frac(num: int, den: int) -> str:
    return f"{num} / {den}" if den else "N/A"


def task_success(path: Path, label: str) -> str:
    """Y = 1, Partial = 0.5, N = 0 from the eyeball CSV (columns: label, golden_id, grade)."""
    if not path.exists():
        return "pending"
    grades = [r["grade"].strip().upper() for r in csv.DictReader(path.open()) if r["label"] == label]
    if not grades:
        return "pending"
    y, part = grades.count("Y"), grades.count("PARTIAL") + grades.count("P")
    return f"{y} Y + {part} Partial / {len(grades)}"


def kpis(conn: sqlite3.Connection, label: str, sources: dict, grades: Path) -> dict:
    cur = conn.execute("SELECT * FROM rag_runs WHERE label = ? ORDER BY golden_id", (label,))
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    if not rows:
        raise SystemExit(f"no rag_runs rows for label {label!r}")
    oos = {g for g, v in sources.items() if v.get("out_of_scope")}
    answerable = [r for r in rows if r["golden_id"] not in oos]
    hits = [r for r in answerable if r["hit_doc"] is not None]
    supported = [r for r in rows if r["support"] is not None]
    lat = [r["latency_s"] for r in rows if r["latency_s"] is not None]
    acc = conn.execute("SELECT AVG(accuracy), AVG(groundedness), COUNT(*) FROM eval_runs WHERE eval_run_label = ?",
                       (label,)).fetchone()
    p50, p95 = nearest_rank(lat, 50), nearest_rank(lat, 95)
    return {
        "label": label, "condition": rows[0]["condition"], "n": len(rows),
        "chunking": f"{rows[0]['chunk_size']}/{rows[0]['chunk_overlap']}" if rows[0]["chunk_size"] else "-",
        "retrieval_hit_rate": _frac(sum(r["hit_doc"] for r in hits), len(hits)),
        "page_hit_rate": _frac(sum(r["hit_page"] for r in hits), len(hits)),
        "grounded_rate": (f"{sum(r['support'] == 'full' for r in supported)} / {len(supported)}"
                          f" ({sum(r['support'] == 'partial' for r in supported)} partial)") if supported else "N/A",
        "correct_refusals": _frac(sum(r["declined"] for r in rows if r["golden_id"] in oos),
                                  sum(1 for r in rows if r["golden_id"] in oos)),
        "unnecessary_refusals": _frac(sum(r["declined"] for r in answerable), len(answerable)),
        "cost_per_query": f"${sum(r['candidate_cost_usd'] or 0 for r in rows) / len(rows):.6f}",
        "latency_p50": f"{p50:.2f}s" if p50 is not None else "N/A",
        "latency_p95": f"{p95:.2f}s" if p95 is not None else "N/A",
        "accuracy": f"{acc[0]:.2f} (groundedness {acc[1]:.2f})" if acc[2] else "not judged",
        "task_success": task_success(grades, label),
        "eval_cost_usd": round(sum(r["eval_cost_usd"] or 0 for r in rows), 4),
    }


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="W6 KPIs per RAG eval label")
    p.add_argument("--label", action="append", required=True)
    p.add_argument("--metric", choices=METRICS, help="print one metric only")
    p.add_argument("--plain", action="store_true", help="value only (for scripts)")
    p.add_argument("--json", action="store_true", help="all KPIs as JSON")
    p.add_argument("--db", default="data/answers.db")
    p.add_argument("--sources", default="data/golden_sources.json")
    p.add_argument("--grades", default="docs/kpi/wk6-task-success.csv")
    args = p.parse_args(argv)
    sources = load_golden_sources(args.sources)
    with sqlite3.connect(args.db) as conn:
        results = [kpis(conn, label, sources, Path(args.grades)) for label in args.label]
    if args.json:
        print(json.dumps(results, indent=2))
    elif args.metric:
        for r in results:
            print(r[args.metric] if args.plain else f"{r['label']}: {args.metric} = {r[args.metric]}")
    else:
        keys = [k for k in results[0] if k != "label"]
        print("| KPI | " + " | ".join(r["label"] for r in results) + " |")
        print("|---|" + "---|" * len(results))
        for k in keys:
            print(f"| {k} | " + " | ".join(str(r[k]) for r in results) + " |")


if __name__ == "__main__":
    main()
