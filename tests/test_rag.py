"""tests/test_rag.py — W6 naive RAG: chunking, pages, index, retrieval, API wiring. Offline (fake embedder + fake LLM)."""
import numpy as np
import pytest

from src.pipeline.models import Answer
from src.pipeline.settings import Settings
from src.rag import naive_rag as rag
from src.rag.prompt import format_context, rag_prompt


# ─── chunking ────────────────────────────────────────────────────────────────

def test_chunk_text_slides_with_overlap():
    text = "".join(chr(ord("a") + i % 26) for i in range(1000))
    chunks = rag.chunk_text(text, size=500, overlap=50)
    assert [s for s, _ in chunks] == [0, 450, 900]
    assert chunks[0][1][-50:] == chunks[1][1][:50]                  # the overlap is shared
    assert "".join(c for _, c in chunks).replace(chunks[0][1][-50:], "", 1)  # sanity: non-empty


def test_chunk_text_short_and_invalid():
    assert rag.chunk_text("short", 500, 50) == [(0, "short")]
    assert rag.chunk_text("   ", 500, 50) == []
    with pytest.raises(ValueError):
        rag.chunk_text("x" * 10, size=50, overlap=50)


def test_chunk_document_records_pages():
    pages = ["a" * 300, "b" * 300, "c" * 300]
    chunks = rag.chunk_document("My Doc.pdf", pages, size=250, overlap=0)
    assert chunks[0]["chunk_id"] == "my-doc:p1:c0" and chunks[0]["page_start"] == 1
    straddle = [c for c in chunks if c["page_start"] != c["page_end"]]
    assert straddle and all(c["page_end"] == c["page_start"] + 1 for c in straddle)
    assert chunks[-1]["page_end"] == 3


def test_load_corpus_skips_excluded_and_unknown(tmp_path):
    (tmp_path / "keep.txt").write_text("alpha beta gamma " * 50)
    (tmp_path / "SAFR.pdf").write_bytes(b"not read: excluded")
    (tmp_path / "notes.docx").write_text("ignored suffix")
    chunks = rag.load_corpus(tmp_path, size=200, overlap=20)
    assert {c["source"] for c in chunks} == {"keep.txt"}


# ─── embedding, index, retrieval ─────────────────────────────────────────────

def test_fake_embed_is_unit_norm_and_similar_for_shared_words():
    v = rag.fake_embed(["fairness ethics accountability", "fairness ethics", "espresso latte"])
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0)
    assert v[0] @ v[1] > v[0] @ v[2]


def test_top_k_orders_by_cosine():
    vecs = np.eye(3, dtype=np.float32)
    index = rag.RagIndex(vecs, [{"chunk_id": f"c{i}"} for i in range(3)])
    hits = rag.top_k(np.array([0.1, 0.9, 0.3], dtype=np.float32), index, k=2)
    assert [h["chunk_id"] for h in hits] == ["c1", "c2"] and hits[0]["score"] == pytest.approx(0.9)


@pytest.fixture
def tiny_index(tmp_path):
    (tmp_path / "corpus").mkdir()
    (tmp_path / "corpus" / "feat.txt").write_text("FEAT means fairness ethics accountability transparency. " * 10)
    (tmp_path / "corpus" / "pdpa.txt").write_text("The PDPA research exception has four conditions. " * 10)
    import asyncio
    index = asyncio.run(rag.build_index(tmp_path / "corpus", Settings(use_fake=True), size=120, overlap=20))
    rag.save_index(index, tmp_path / "idx" / "tiny")
    return tmp_path / "idx" / "tiny"


def test_save_load_round_trip(tiny_index):
    index = rag.load_index(tiny_index)
    assert index.vectors.shape == (index.meta["n_chunks"], rag.FAKE_DIM)
    assert index.meta["embedder"] == "fake" and index.meta["chunk_size"] == 120


@pytest.mark.asyncio
async def test_retrieve_finds_the_right_document(tiny_index):
    index = rag.load_index(tiny_index)
    hits, cost = await rag.retrieve("what does FEAT fairness ethics mean", index, Settings(use_fake=True), k=2)
    assert hits[0]["source"] == "feat.txt" and cost == 0.0


@pytest.mark.asyncio
async def test_retrieve_rejects_embedder_mismatch(tiny_index):
    index = rag.load_index(tiny_index)
    with pytest.raises(ValueError):
        await rag.retrieve("q", index, Settings(use_fake=False), k=1)


# ─── prompt + citations ──────────────────────────────────────────────────────

def test_format_context_and_prompt():
    hits = [{"chunk_id": "doc:p5:c1", "source": "Doc.pdf", "page_start": 5, "page_end": 6, "text": "Hello."}]
    ctx = format_context(hits)
    assert ctx.startswith("[doc:p5:c1] (Doc.pdf, p.5-6)\nHello.")
    assert rag_prompt("Q?", ctx).endswith("QUESTION: Q?") and "ONLY the context" in rag_prompt("Q?", ctx)


def test_cited_sources_drops_invented_ids():
    hits = [{"chunk_id": "a:p1:c0"}, {"chunk_id": "b:p2:c3"}]
    ans = Answer(content="x", sources=["[a:p1:c0]", "made-up:p9:c9", "a:p1:c0"])
    assert rag.cited_sources(ans, hits) == ["a:p1:c0"]


# ─── API wiring (fake LLM + fake embedder) ───────────────────────────────────

@pytest.fixture
def rag_client(tiny_index, monkeypatch):
    import api.main
    from fastapi.testclient import TestClient
    monkeypatch.setattr(api.main, "_index", rag.load_index(tiny_index))
    return TestClient(api.main.app)


def test_metrics_report_retrieval_and_health_is_unchanged(rag_client):
    assert rag_client.get("/health").json() == {"status": "ok"}
    assert rag_client.get("/metrics").json()["retrieval"]["chunks"] > 0


def test_ask_batched_uses_retrieval(rag_client):
    r = rag_client.post("/ask_batched", json={"question": "FEAT fairness?"})
    assert r.status_code == 200 and r.json()["schema_version"] == "v1"   # contract unchanged


def test_ask_stream_ends_with_passages(rag_client):
    text = rag_client.post("/ask", json={"question": "PDPA research exception?"}).text
    assert "Retrieved passages:" in text and "pdpa.txt" in text


def test_missing_index_fails_loudly(tmp_path):
    import api.main
    with pytest.raises(RuntimeError, match="build_index"):
        api.main._load_rag_index(Settings(use_fake=True, rag_index=tmp_path / "nope"))


# ─── W7: sentence chunker, embedding-model choice ─────────────────────────────

def test_chunk_sentences_never_splits_a_sentence():
    text = "First sentence here. Second one is a bit longer than the first. Third. " * 5
    chunks = rag.chunk_sentences(text, size=80)
    assert all(len(c) <= 80 for _, c in chunks)
    assert all(c.rstrip().endswith(".") for _, c in chunks)              # ends on a boundary
    assert all(text[s:s + len(c)] == c for s, c in chunks)               # spans of the original text


def test_chunk_sentences_windows_an_oversized_sentence():
    long = "Word " + "word " * 60 + "end."                               # one 309-char sentence (capitalised: a new sentence)
    chunks = rag.chunk_sentences("Short. " + long, size=100)
    assert chunks[0][1] == "Short." and all(len(c) <= 100 for _, c in chunks)


def test_build_index_records_chunker_and_rejects_unknown(tmp_path):
    import asyncio
    (tmp_path / "a.txt").write_text("One sentence. Two sentences here. " * 20)
    index = asyncio.run(rag.build_index(tmp_path, Settings(use_fake=True), size=120, chunker="sentence"))
    assert index.meta["chunker"] == "sentence" and index.meta["chunk_overlap"] == 0
    with pytest.raises(ValueError):
        asyncio.run(rag.build_index(tmp_path, Settings(use_fake=True), model="text-embedding-ada-002"))


@pytest.mark.asyncio
async def test_local_model_is_routed_locally_and_free(monkeypatch):
    calls = []
    monkeypatch.setattr(rag, "embed_local", lambda texts, model: calls.append(model) or rag.fake_embed(texts))
    vecs, cost = await rag.embed_texts(["hello"], Settings(use_fake=False), model="local:minilm")
    assert calls == ["local:minilm"] and cost == 0.0 and vecs.shape[0] == 1


def test_stream_path_asks_for_inline_citations():
    from src.pipeline.llm import user_message
    tool = user_message("Q?", "[a:p1:c0] (A.pdf, p.1)\ntext")["content"]
    stream = user_message("Q?", "[a:p1:c0] (A.pdf, p.1)\ntext", inline_citations=True)["content"]
    assert "`sources`" in tool and "square brackets" not in tool          # W6 tool-call prompt unchanged
    assert "After each fact, cite the id" in stream and "`sources`" not in stream
    assert user_message("Q?")["content"] == "Q?"                          # no context: bare question

