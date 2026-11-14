"""src/rag/naive_rag.py — naive RAG for the capstone (W6).

The same pipeline as the W6 Track A notebook — chunk → embed → store → cosine
top-K → grounded prompt — placed in the capstone (Application Growth Guide).
No frameworks, no vector DB: an in-memory NumPy matrix (W7/W8 replace it).

Capstone changes from the guide's version, and why:
  • The corpus is 15 PDFs, not .md/.txt: text comes from pypdf, page by page,
    and every chunk keeps the PDF pages it spans, so retrieval can be checked
    against the golden set's cited pages.
  • Vectors are stored as a float32 .npy next to a small .json of chunk
    metadata. ~4,500 chunks × 1,536 floats as JSON would be over 100 MB.
  • Retrieval is one matrix-vector product, not a Python loop over chunks.
  • Generation stays in src/pipeline/llm.py (tool-calling Answer, prompt v2):
    retrieval only adds a context block to the question, so the API contract
    (ADR 0002, schema v1) is unchanged.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from src.pipeline.cost import compute_embed_cost_usd
from src.pipeline.llm import _client, ask_llm
from src.pipeline.models import Answer, Question
from src.pipeline.settings import Settings
from src.rag.prompt import format_context

logger = logging.getLogger(__name__)

EMBED_MODEL = "text-embedding-3-small"      # 1,536 dims, $0.02 per 1M tokens
FAKE_DIM = 64                               # offline tests (PIPELINE_USE_FAKE=1)
EMBED_BATCH = 200                           # chunks per embeddings request
# SAFR v1.0 is superseded by v1.1 (data/corpus/SOURCES.md, note 2): keep the two from competing.
DEFAULT_EXCLUDE = frozenset({"SAFR.pdf"})
CORPUS_SUFFIXES = (".pdf", ".md", ".txt")


# ─── Chunking ────────────────────────────────────────────────────────────────

def chunk_text(text: str, size: int = 500, overlap: int = 50) -> list[tuple[int, str]]:
    """Sliding window over characters. Returns (start offset, chunk) pairs.

    Cuts mid-sentence on purpose (naive); W7 brings structure-aware chunking.
    """
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError(f"need size > 0 and 0 <= overlap < size; got size={size}, overlap={overlap}")
    if len(text) <= size:
        return [(0, text)] if text.strip() else []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if text[start:end].strip():
            chunks.append((start, text[start:end]))
        if end == len(text):
            break
        start = end - overlap
    return chunks


# ─── Corpus loading ──────────────────────────────────────────────────────────

def doc_slug(filename: str) -> str:
    """'FEAT Principles Final.pdf' -> 'feat-principles-final': a short, URL-safe document id."""
    return re.sub(r"[^a-z0-9]+", "-", Path(filename).stem.lower()).strip("-")


def read_pages(path: Path) -> list[str]:
    """Text of each page, whitespace collapsed. A .md/.txt file is one 'page'."""
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return [" ".join((page.extract_text() or "").split()) for page in PdfReader(str(path)).pages]
    return [" ".join(path.read_text(encoding="utf-8").split())]


def chunk_document(filename: str, pages: list[str], size: int, overlap: int) -> list[dict]:
    """Join a document's pages, chunk the whole text, and record the pages each chunk spans."""
    starts, parts, pos = [], [], 0
    for text in pages:
        starts.append(pos)
        parts.append(text)
        pos += len(text) + 1                                   # +1 for the joining space
    full = " ".join(parts)
    page_ends = [s + len(t) for s, t in zip(starts, parts)]

    def page_at(offset: int) -> int:                           # 1-based PDF page holding `offset`
        for i, end in enumerate(page_ends):
            if offset < end + 1:
                return i + 1
        return len(pages)

    slug = doc_slug(filename)
    chunks = []
    for idx, (start, text) in enumerate(chunk_text(full, size, overlap)):
        first, last = page_at(start), page_at(start + len(text) - 1)
        chunks.append({"chunk_id": f"{slug}:p{first}:c{idx}", "source": filename,
                       "page_start": first, "page_end": last, "text": text})
    return chunks


def load_corpus(corpus_dir: str | Path, size: int = 500, overlap: int = 50,
                exclude: frozenset[str] = DEFAULT_EXCLUDE) -> list[dict]:
    """Chunk every PDF / .md / .txt in corpus_dir (sorted, so ids are stable)."""
    chunks = []
    for path in sorted(Path(corpus_dir).iterdir()):
        if path.suffix.lower() not in CORPUS_SUFFIXES or path.name in exclude:
            continue
        chunks.extend(chunk_document(path.name, read_pages(path), size, overlap))
    return chunks


# ─── Embedding ───────────────────────────────────────────────────────────────

def _normalise(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    return (m / np.where(norms == 0, 1.0, norms)).astype(np.float32)


def fake_embed(texts: list[str]) -> np.ndarray:
    """Deterministic offline embedding: hashed bag of words. Shared words → higher cosine."""
    m = np.zeros((len(texts), FAKE_DIM), dtype=np.float32)
    for i, t in enumerate(texts):
        for w in re.findall(r"[a-z0-9]+", t.lower()):
            m[i, int(hashlib.md5(w.encode()).hexdigest(), 16) % FAKE_DIM] += 1.0
    return _normalise(m)


async def embed_texts(texts: list[str], settings: Settings,
                      model: str = EMBED_MODEL) -> tuple[np.ndarray, float]:
    """Embed in batches. Returns (unit-norm float32 matrix, cost in USD)."""
    if settings.use_fake:
        return fake_embed(texts), 0.0
    client, rows, tokens = _client(settings), [], 0
    for i in range(0, len(texts), EMBED_BATCH):
        resp = await client.embeddings.create(model=model, input=texts[i:i + EMBED_BATCH])
        rows.extend(item.embedding for item in resp.data)
        tokens += resp.usage.prompt_tokens if resp.usage else 0
    return _normalise(np.array(rows, dtype=np.float32)), compute_embed_cost_usd(model, tokens)


# ─── The index: vectors + chunk metadata ─────────────────────────────────────

@dataclass
class RagIndex:
    vectors: np.ndarray                      # (n_chunks, dim), unit norm
    chunks: list[dict]                       # same order as vectors; no vectors inside
    meta: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.chunks)


async def build_index(corpus_dir: str | Path, settings: Settings, size: int = 500, overlap: int = 50,
                      exclude: frozenset[str] = DEFAULT_EXCLUDE, model: str = EMBED_MODEL) -> RagIndex:
    """Chunk the corpus and embed every chunk. The one-off, index-time pass."""
    t0 = time.perf_counter()
    chunks = load_corpus(corpus_dir, size, overlap, exclude)
    if not chunks:
        raise ValueError(f"no chunks: is {corpus_dir} empty?")
    vectors, cost = await embed_texts([c["text"] for c in chunks], settings, model)
    meta = {
        "embedder": "fake" if settings.use_fake else model, "dim": int(vectors.shape[1]),
        "chunk_size": size, "chunk_overlap": overlap, "n_chunks": len(chunks),
        "documents": sorted({c["source"] for c in chunks}), "excluded": sorted(exclude),
        "embed_cost_usd": round(cost, 6), "build_seconds": round(time.perf_counter() - t0, 1),
    }
    return RagIndex(vectors, chunks, meta)


def save_index(index: RagIndex, prefix: str | Path) -> tuple[Path, Path]:
    """Write <prefix>.npy (vectors) and <prefix>.json (meta + chunks)."""
    prefix = Path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    npy, js = prefix.with_suffix(".npy"), prefix.with_suffix(".json")
    np.save(npy, index.vectors)
    js.write_text(json.dumps({"meta": index.meta, "chunks": index.chunks}, ensure_ascii=False), encoding="utf-8")
    return npy, js


def load_index(prefix: str | Path) -> RagIndex:
    """Load an index saved by save_index; checks that vectors and chunks line up."""
    prefix = Path(prefix)
    vectors = np.load(prefix.with_suffix(".npy"))
    data = json.loads(prefix.with_suffix(".json").read_text(encoding="utf-8"))
    if len(data["chunks"]) != vectors.shape[0]:
        raise ValueError(f"{prefix}: {len(data['chunks'])} chunks but {vectors.shape[0]} vectors")
    return RagIndex(vectors, data["chunks"], data["meta"])


# ─── Retrieval ───────────────────────────────────────────────────────────────

def top_k(query_vec: np.ndarray, index: RagIndex, k: int = 3) -> list[dict]:
    """Cosine = dot product on unit vectors: one matrix-vector product scores every chunk."""
    scores = index.vectors @ query_vec
    best = np.argsort(scores)[::-1][:k]
    return [{**index.chunks[i], "score": round(float(scores[i]), 4)} for i in best]


async def retrieve(question: str, index: RagIndex, settings: Settings, k: int = 3) -> tuple[list[dict], float]:
    """Embed the question (same model as the index) and return (top-K hits, embedding cost)."""
    model = index.meta.get("embedder", EMBED_MODEL)
    if (model == "fake") != settings.use_fake:
        raise ValueError(f"index embedder {model!r} doesn't match use_fake={settings.use_fake}")
    vecs, cost = await embed_texts([question], settings, model=EMBED_MODEL if model == "fake" else model)
    return top_k(vecs[0], index, k), cost


# ─── Generation ──────────────────────────────────────────────────────────────

def cited_sources(answer: Answer, hits: list[dict]) -> list[str]:
    """The ids the model cited, kept only if they were actually retrieved (no invented citations)."""
    retrieved = {h["chunk_id"] for h in hits}
    kept = [s.strip("[] ") for s in answer.sources if s.strip("[] ") in retrieved]
    dropped = [s for s in answer.sources if s.strip("[] ") not in retrieved]
    if dropped:
        logger.info("dropped %d cited source(s) not in the retrieved set: %s", len(dropped), dropped)
    return list(dict.fromkeys(kept))


@dataclass
class RagResult:
    answer: Answer
    hits: list[dict]
    embed_cost_usd: float
    latency_s: float


async def rag_answer(question: str, index: RagIndex, settings: Settings, k: int = 3) -> RagResult:
    """retrieve → grounded prompt → tool-calling Answer. What /ask_batched and the eval both call."""
    t0 = time.perf_counter()
    hits, embed_cost = await retrieve(question, index, settings, k)
    answer = await ask_llm(Question(question=question), settings, context=format_context(hits))
    answer.sources = cited_sources(answer, hits)
    answer.cost_usd += embed_cost                            # the query embedding is part of the bill
    return RagResult(answer, hits, embed_cost, time.perf_counter() - t0)
