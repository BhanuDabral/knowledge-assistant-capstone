"""scripts/migrate_to_qdrant.py — copy a built index into Qdrant, then prove nothing changed (W7).

Reads <index>.npy + <index>.json (scripts/build_index.py), upserts every vector with
its chunk metadata as payload into a Qdrant collection (cosine, HNSW defaults), and
re-embeds nothing ($0 for the copy).

Then the parity check (Growth Guide: "retrieval hit rate must be unchanged"), made
stricter: every golden question is searched in both stores and the top-K chunk ids
must match. Storage changed, not retrieval, so any difference is a migration bug.
The check embeds 20 questions (~$0.00001).

Usage (QDRANT_URL + QDRANT_API_KEY in .env):
    python scripts/migrate_to_qdrant.py                                       # data/index/medium → capstone_chunks
    python scripts/migrate_to_qdrant.py --index data/index/small-sentence --collection capstone_small_sentence
    python scripts/migrate_to_qdrant.py --recreate                            # drop and rebuild the collection
"""
import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.eval.golden import load_golden
from src.pipeline.settings import Settings
from src.rag.naive_rag import embed_texts, load_index
from src.rag.qdrant_store import DEFAULT_COLLECTION, get_client, upsert_index


async def parity(index, qindex, questions: list[str], settings: Settings, k: int) -> list[tuple]:
    """(question, numpy top-k ids, qdrant top-k ids, max score difference) per question."""
    vecs, _ = await embed_texts(questions, settings, model=index.meta["embedder"])
    rows = []
    for q, v in zip(questions, vecs):
        a, b = index.search(v, k), qindex.search(v, k)
        rows.append((q, [h["chunk_id"] for h in a], [h["chunk_id"] for h in b],
                     max(abs(x["score"] - y["score"]) for x, y in zip(a, b))))
    return rows


async def main(args) -> int:
    settings = Settings()
    index = load_index(args.index)
    print(f"Loaded {args.index}: {len(index)} chunks · {index.meta.get('embedder')} · "
          f"{index.meta.get('chunker', 'fixed')} {index.meta.get('chunk_size')}/{index.meta.get('chunk_overlap')}")
    client = get_client(args.location)
    t0 = time.perf_counter()
    qindex = upsert_index(index, args.collection, client, recreate=args.recreate)
    n = len(qindex)
    print(f"Upserted into Qdrant collection {args.collection!r}: {n} points, dim {qindex.meta['dim']}, cosine "
          f"· {time.perf_counter() - t0:.1f}s")
    if n != len(index):
        print(f"FAIL: {n} points in Qdrant but {len(index)} chunks in the index")
        return 1
    questions = [e.question for e in load_golden(args.golden_set)]
    rows = await parity(index, qindex, questions, settings, args.k)
    same = sum(a == b for _, a, b, _ in rows)
    print(f"\nParity check, top-{args.k} on {len(rows)} golden questions: {same}/{len(rows)} identical "
          f"(max score difference {max(d for *_, d in rows):.4f})")
    for q, a, b, d in rows:
        if a != b:
            print(f"  differs: {q[:60]}\n    numpy:  {a}\n    qdrant: {b}")
    return 0 if same == len(rows) else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="W7: migrate a NumPy index into Qdrant and check parity")
    p.add_argument("--index", default="data/index/medium")
    p.add_argument("--collection", default=DEFAULT_COLLECTION)
    p.add_argument("--recreate", action="store_true", help="drop the collection first")
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--golden-set", default="data/golden_set.jsonl")
    p.add_argument("--location", help="override the connection, e.g. ':memory:' (tests)")
    raise SystemExit(asyncio.run(main(p.parse_args())))
