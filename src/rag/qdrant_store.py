"""src/rag/qdrant_store.py — Qdrant as the capstone's vector store (W7).

Replaces W6's in-memory NumPy matrix with a Qdrant collection: vectors persist on
Qdrant's side, search uses its HNSW index, and every chunk's metadata travels as
payload (ready for W8's filtering). W6's RagIndex stays as the reference backend.

Both backends expose the same small interface, so retrieval, the API and the eval
don't care which one they hold:
    index.meta          embedder / chunker / sizes (from the build)
    len(index)          number of chunks
    index.search(q, k)  top-k chunk dicts with a cosine "score"

Connection (Growth Guide order, plus an embedded mode for tests and offline use):
    QDRANT_URL + QDRANT_API_KEY   → Qdrant Cloud
    QDRANT_URL only               → a local Qdrant server (Docker)
    QDRANT_PATH                   → embedded, on-disk (no server)
    nothing set                   → error: the API never silently falls back
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np

QDRANT_PREFIX = "qdrant:"           # index spec "qdrant:<collection>" (API, eval, migration)
DEFAULT_COLLECTION = "capstone_chunks"
UPSERT_BATCH = 256
# W7, measured: with Qdrant's default search effort, HNSW missed the true top-2 for g019 on the
# W6 baseline collection (parity 19/20); hnsw_ef=256 restores 20/20 on both collections at the same
# ~106 ms median (the network dominates). Override with PIPELINE_QDRANT_HNSW_EF; 0 = exact search.
DEFAULT_HNSW_EF = 256
# Build settings copied into every point's payload, so a collection describes itself.
META_KEYS = ("embedder", "chunker", "chunk_size", "chunk_overlap")


def search_params():
    """HNSW search effort (hnsw_ef) from PIPELINE_QDRANT_HNSW_EF; 0 means exact (brute-force) search."""
    from qdrant_client.models import SearchParams
    ef = int(os.environ.get("PIPELINE_QDRANT_HNSW_EF", DEFAULT_HNSW_EF))
    return SearchParams(exact=True) if ef == 0 else SearchParams(hnsw_ef=ef)


def get_client(location: str | None = None):
    """A QdrantClient from the environment, or `location` (e.g. ":memory:" in tests)."""
    from qdrant_client import QdrantClient
    if location:
        return QdrantClient(location=location)
    url, key, path = (os.environ.get(v, "").strip() for v in ("QDRANT_URL", "QDRANT_API_KEY", "QDRANT_PATH"))
    if url:
        return QdrantClient(url=url, api_key=key or None, timeout=30)
    if path:
        return QdrantClient(path=path)
    raise RuntimeError("Qdrant not configured: set QDRANT_URL (+ QDRANT_API_KEY for Qdrant Cloud) in .env")


@dataclass
class QdrantIndex:
    """A Qdrant collection behind the same interface as naive_rag.RagIndex."""
    client: object
    collection: str
    meta: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return self.client.count(self.collection, exact=True).count

    def search(self, query_vec: np.ndarray, k: int = 3) -> list[dict]:
        """Qdrant's HNSW search; cosine scores, same hit shape as RagIndex.search."""
        points = self.client.query_points(collection_name=self.collection, query=query_vec.tolist(),
                                          limit=k, with_payload=True, search_params=search_params()).points
        return [{**{key: p.payload[key] for key in ("chunk_id", "source", "page_start", "page_end", "text")},
                 "score": round(float(p.score), 4)} for p in points]

    @classmethod
    def connect(cls, collection: str = DEFAULT_COLLECTION, client=None) -> "QdrantIndex":
        """Open an existing collection; its build settings come from a point's payload."""
        client = client or get_client()
        if not client.collection_exists(collection):
            raise RuntimeError(f"Qdrant collection {collection!r} not found; "
                               f"run: python scripts/migrate_to_qdrant.py --collection {collection}")
        sample, _ = client.scroll(collection, limit=1, with_payload=True)
        meta = {k: sample[0].payload.get(k) for k in META_KEYS} if sample else {}
        meta["dim"] = client.get_collection(collection).config.params.vectors.size
        meta["backend"], meta["collection"] = "qdrant", collection
        return cls(client, collection, meta)


def upsert_index(index, collection: str, client=None, recreate: bool = False) -> "QdrantIndex":
    """Copy a built RagIndex (vectors + chunks) into a Qdrant collection. No re-embedding.

    Cosine distance (the W7 default: robust even if a vector weren't normalised).
    Point ids are the chunk positions, so re-running overwrites rather than duplicates.
    """
    from qdrant_client.models import Distance, PointStruct, VectorParams
    client = client or get_client()
    dim = int(index.vectors.shape[1])
    if recreate and client.collection_exists(collection):
        client.delete_collection(collection)
    if not client.collection_exists(collection):
        client.create_collection(collection, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))
    existing = client.get_collection(collection).config.params.vectors.size
    if existing != dim:
        raise ValueError(f"collection {collection!r} has dim {existing}, index has {dim}: use recreate=True")
    build = {k: index.meta.get(k) for k in META_KEYS}
    for start in range(0, len(index.chunks), UPSERT_BATCH):
        batch = range(start, min(start + UPSERT_BATCH, len(index.chunks)))
        client.upsert(collection, points=[
            PointStruct(id=i, vector=index.vectors[i].tolist(), payload={**index.chunks[i], **build})
            for i in batch], wait=True)
    return QdrantIndex.connect(collection, client)


def open_index(spec: str, client=None):
    """'qdrant:<collection>' → QdrantIndex; anything else → a W6 NumPy index at that path prefix."""
    if spec.startswith(QDRANT_PREFIX):
        return QdrantIndex.connect(spec[len(QDRANT_PREFIX):] or DEFAULT_COLLECTION, client)
    from src.rag.naive_rag import load_index
    return load_index(spec)
