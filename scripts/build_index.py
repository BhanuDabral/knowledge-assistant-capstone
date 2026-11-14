"""scripts/build_index.py — build the naive RAG index (W6). Run once, or when the corpus changes.

Chunks every PDF in the corpus (sliding window), embeds each chunk with
text-embedding-3-small and writes <out>.npy (vectors) + <out>.json (metadata).
SAFR.pdf (v1.0, superseded by v1.1) is excluded by default.

Usage:
    python scripts/build_index.py                                   # 500/50 -> data/index/medium
    python scripts/build_index.py --size 300 --overlap 30 --out data/index/small
    python scripts/build_index.py --size 800 --overlap 80 --out data/index/large
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline.settings import Settings
from src.rag.naive_rag import DEFAULT_EXCLUDE, build_index, save_index


async def main(args) -> None:
    settings = Settings()
    exclude = frozenset(args.exclude) if args.exclude is not None else DEFAULT_EXCLUDE
    print(f"Chunking {args.corpus} (size={args.size}, overlap={args.overlap}; excluding {sorted(exclude)})"
          f" and embedding with {'the FAKE embedder' if settings.use_fake else 'text-embedding-3-small'}...")
    index = await build_index(args.corpus, settings, args.size, args.overlap, exclude)
    npy, js = save_index(index, args.out)
    m = index.meta
    print(f"  {m['n_chunks']} chunks from {len(m['documents'])} documents · dim {m['dim']}"
          f" · embed cost ${m['embed_cost_usd']:.4f} · {m['build_seconds']}s")
    print(f"  wrote {npy} ({npy.stat().st_size / 1e6:.1f} MB) and {js} ({js.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="W6: build the naive RAG index")
    p.add_argument("--corpus", default="data/corpus/raw")
    p.add_argument("--size", type=int, default=500)
    p.add_argument("--overlap", type=int, default=50)
    p.add_argument("--out", default="data/index/medium", help="path prefix: writes <out>.npy and <out>.json")
    p.add_argument("--exclude", nargs="*", default=None, help=f"file names to skip (default: {sorted(DEFAULT_EXCLUDE)})")
    asyncio.run(main(p.parse_args()))
