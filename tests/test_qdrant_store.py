"""tests/test_qdrant_store.py — Qdrant backend (W7) in Qdrant's in-memory mode. Offline: no server, no cloud."""
import asyncio

import numpy as np
import pytest

from src.pipeline.settings import Settings
from src.rag import naive_rag as rag
from src.rag import qdrant_store as qs

# In-memory Qdrant always searches exactly, so it warns that hnsw_ef has no effect: expected here.
pytestmark = pytest.mark.filterwarnings("ignore:Local mode performs exact:UserWarning")


@pytest.fixture
def built(tmp_path):
    (tmp_path / "feat.txt").write_text("FEAT means fairness ethics accountability transparency. " * 10)
    (tmp_path / "pdpa.txt").write_text("The PDPA research exception has four conditions. " * 10)
    return asyncio.run(rag.build_index(tmp_path, Settings(use_fake=True), size=120, overlap=20))


@pytest.fixture
def client():
    return qs.get_client(":memory:")


def test_upsert_copies_every_chunk_with_build_settings(built, client):
    q = qs.upsert_index(built, "t", client)
    assert len(q) == len(built)
    assert q.meta["embedder"] == "fake" and q.meta["chunk_size"] == 120 and q.meta["dim"] == rag.FAKE_DIM


def test_qdrant_search_matches_numpy_search(built, client):
    q = qs.upsert_index(built, "t", client)
    for text in ("what does FEAT fairness mean", "PDPA research exception conditions"):
        v = rag.fake_embed([text])[0]
        assert [h["chunk_id"] for h in q.search(v, 3)] == [h["chunk_id"] for h in built.search(v, 3)]


def test_rerun_overwrites_and_dim_mismatch_needs_recreate(built, client):
    qs.upsert_index(built, "t", client)
    assert len(qs.upsert_index(built, "t", client)) == len(built)          # ids reused: no duplicates
    other = rag.RagIndex(np.ones((1, 8), dtype=np.float32) / np.sqrt(8), [built.chunks[0]], dict(built.meta))
    with pytest.raises(ValueError):
        qs.upsert_index(other, "t", client)
    assert len(qs.upsert_index(other, "t", client, recreate=True)) == 1


@pytest.mark.asyncio
async def test_retrieve_works_through_qdrant(built, client):
    q = qs.upsert_index(built, "t", client)
    hits, _ = await rag.retrieve("FEAT fairness ethics", q, Settings(use_fake=True), k=2)
    assert hits[0]["source"] == "feat.txt" and set(hits[0]) >= {"chunk_id", "page_start", "text", "score"}


def test_open_index_dispatches_and_missing_collection_fails(built, client, tmp_path):
    qs.upsert_index(built, "t", client)
    assert isinstance(qs.open_index("qdrant:t", client), qs.QdrantIndex)
    rag.save_index(built, tmp_path / "idx")
    assert isinstance(qs.open_index(str(tmp_path / "idx")), rag.RagIndex)
    with pytest.raises(RuntimeError, match="migrate_to_qdrant"):
        qs.QdrantIndex.connect("missing", client)


def test_unconfigured_client_fails_loudly(monkeypatch):
    for v in ("QDRANT_URL", "QDRANT_API_KEY", "QDRANT_PATH"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(RuntimeError, match="QDRANT_URL"):
        qs.get_client()


def test_search_params_default_and_override(monkeypatch):
    monkeypatch.delenv("PIPELINE_QDRANT_HNSW_EF", raising=False)
    assert qs.search_params().hnsw_ef == qs.DEFAULT_HNSW_EF == 256
    monkeypatch.setenv("PIPELINE_QDRANT_HNSW_EF", "0")
    assert qs.search_params().exact is True

