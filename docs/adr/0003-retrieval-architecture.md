# ADR-0003: Retrieval architecture — embedding model, chunker, vector store

- **Status:** Draft (W7) · to be locked at M2 (W12, DR #2)
- **Date:** 2026-11-14
- **Author:** Bhanu Dabral
- **Related:** ADR 0001 §4 (Phase 2 comparison design), §12 (W6 naive RAG); `docs/kpi/wk7-snapshot.md`

> Drafted by Claude Code from the W7 measurements — review and reword.

## 1. Context

W6 shipped naive RAG: `text-embedding-3-small`, a fixed 500/50 character window, cosine top-3 over a NumPy
matrix held in memory. W7 asks two questions about the retrieval layer, without changing what the app does:

1. Which **embedding model** and **chunker** should the capstone use? (measured, not assumed)
2. Should the vectors move from a NumPy matrix to a **vector database**, and which one?

Every option was run through the W6 harness (`scripts/run_rag_eval.py`): 20 golden questions, gpt-4o judge
(rubric v2, unchanged so W7 is comparable with W6), citation support, refusal checks, latency and cost.

## 2. Decision

| Layer | Choice | Was (W6) |
|---|---|---|
| Embedding model | **text-embedding-3-small** (1,536 dims, $0.02 / 1M tokens) | same |
| Chunker | **sentence-aware**, ≤ 500 characters, whole sentences only | fixed 500/50 window |
| Vector store | **Qdrant Cloud** (free tier), collection `capstone_chunks`, 5,228 points | NumPy matrix in memory |
| Distance | **cosine** | cosine (dot product on unit vectors) |
| Index | HNSW, Qdrant defaults (m = 16, ef_construct = 100); search with **hnsw_ef = 256** | linear scan |
| Payload | chunk id, source, page span, text, embedder, chunker (ready for W8 filters) | JSON file |

Selected with `PIPELINE_RAG_INDEX=qdrant:capstone_chunks`; the W6 NumPy index stays as the reference backend
(`PIPELINE_RAG_INDEX=data/index/medium`), and the W6 vectors are kept in Qdrant as `capstone_w6_baseline`.

## 3. Evidence: the embedder × chunker grid

| Embedder × chunker | Chunks | Doc hit | Page hit | Accuracy (judge, 1–4) | Fully supported | Unneeded refusals | Cost / q |
|---|---|---|---|---|---|---|---|
| **3-small × fixed (W6 baseline)** | 4,428 | 17/18 | 14/18 | 2.55 · repeat 2.35 → **2.45** | 11/17 · 10/17 | 1/18 | $0.00018 |
| **3-small × sentence (chosen)** | 5,228 | 17/18 | **15/18** | 2.55 | 9/17 | 1/18 | $0.00017 |
| 3-large × fixed | 4,428 | 17/18 | 15/18 | 2.50 | 10/17 | 1/18 | $0.00018 |
| 3-large × sentence | 5,228 | 17/18 | 15/18 | 2.70 · repeat 2.45 → 2.58 | 10/17 · 11/17 | 1/18 | $0.00017 |
| local MiniLM × fixed | 4,428 | 17/18 | 12/18 | 2.35 | 8/15 | 3/18 | $0.00018 |
| local MiniLM × sentence | 5,228 | 17/18 | 11/18 | 2.00 | 6/17 | 1/18 | $0.00017 |

**On Qdrant (the chosen default, `qdrant:capstone_chunks`):** the full eval retrieved exactly the same chunks as
the NumPy index for 20/20 questions; accuracy 2.70 (NumPy, same retrieval: 2.55), fully supported 10/17, refusals
2/2 correct and 1/18 unnecessary, $0.00017 per query, p50 3.13 s / p95 3.91 s. The UI's stream path on Qdrant:
accuracy 2.25, passage named in 16/20 answers (inline citations, W7), 2/18 unnecessary refusals.

**Run-to-run noise with retrieval:** the same configuration moved 0.20–0.25 in accuracy between two runs
(retrieval itself is deterministic: page hits were identical across repeats; generation and the judge vary).
Identical retrieval on NumPy and Qdrant still scored 2.55 vs 2.70. Differences smaller than about 0.25 are not
evidence of a better configuration.

## 4. Why these choices

- **Embedding model: keep 3-small.** Document hit is identical in all six cells (17/18, the same g008 miss),
  so the embedder is not the bottleneck for finding the right document. 3-large's best cell averages 2.58 over
  two runs against the baseline's 2.45: a +0.13 gap inside the 0.20–0.25 noise, for 6.5× the embedding price
  (index build $0.055 vs $0.008). The deck's rule (lowest cost within 1–2 points of the best) picks 3-small.
- **Chunker: sentence-aware.** It finds the cited page once more (15/18 vs 14/18) in every run with both OpenAI
  models (retrieval is deterministic, so this is not noise), at equal accuracy and slightly lower cost per query
  (shorter passages). Chunks end on sentence boundaries, so the passages users see read cleanly. Trade-off
  accepted: 18% more chunks (5,228 vs 4,428), and its single run had 9/17 fully supported answers vs 11/17 (within
  the noise; watch it in W8).
- **Vector store: Qdrant.** Persistence and a service the API calls, HNSW for scale, payload filters that W8
  needs, and a free cloud tier. Migration changed nothing: every golden question returns the same top-3 chunks
  from Qdrant as from NumPy (parity 20/20 on both collections), copying the vectors without re-embedding ($0).
- **Search effort: hnsw_ef = 256.** With Qdrant's default effort, HNSW missed the true top-2 for g019 on the
  baseline collection (parity 19/20; exact search matched NumPy). That is HNSW's recall-for-speed trade-off,
  observed on our corpus: g019 is out of scope, so its scores are low and close together. `hnsw_ef = 256`
  restores 20/20 on both collections at the same ~106 ms median query time (the network dominates).
- **Distance: cosine.** Robust even if a future embedder returns unnormalised vectors (the W7 Day 2 "silent bug":
  dot product promoted a vector scaled 3× although its meaning hadn't changed).

## 5. Alternatives rejected

| Alternative | Why not |
|---|---|
| text-embedding-3-large | No measurable gain (+0.13 within 0.20–0.25 noise); 6.5× embedding price; 2× storage |
| Local all-MiniLM-L6-v2 | Worse: page hit 11–12/18, accuracy 2.00–2.35, fewer supported answers. Its real advantage, privacy (nothing leaves the machine), is not required for a public corpus. Revisit if the corpus ever holds confidential documents |
| Fixed 500/50 window | Kept as the reference; sentence-aware finds the cited page more often at no cost |
| FAISS | A library, not a service: no persistence or filtering of its own |
| Chroma | Workable; smaller ecosystem and less proven at scale; the course and W8 build on Qdrant |
| pgvector | Only attractive if Postgres were already in the stack; it isn't |
| Qdrant exact search | Would also give 20/20 at this size, but stops scaling; hnsw_ef = 256 keeps HNSW and full recall on our golden set |

## 6. Consequences

- **Positive:** vectors persist outside the app (no reload at start-up); retrieval scales past what a NumPy
  matrix in RAM can hold; chunk metadata is payload, ready for W8's filters; the W6 backend remains for
  comparison.
- **Negative:** a network hop per query (~106 ms median to Qdrant Cloud); a third-party service and an API key to
  manage; the free tier can be paused when idle.
- **Unchanged:** the API contract (ADR 0002, schema v1), prompt v2, the judge's rubric, the golden set.

## 7. Open questions (for W8–W12)

1. g008 (wrong document) fails in every configuration: will W8 metadata filters or W9 hybrid search fix it?
2. Is 0.20–0.25 accuracy noise too large to decide future changes? More golden questions, or repeated runs per
   change, may be needed (ties to DR #1's "fresh human-scored examples").
3. Does sentence-aware's lower fully-supported count (9/17 vs 11/17, one run) hold up? Re-measure in W8.
4. When the corpus grows, re-check the hnsw_ef setting and whether quantization is worth it.

## 8. Change log

| Date | Version | Change |
|---|---|---|
| 2026-11-14 | Draft | W7: embedder × chunker grid, Qdrant migration, decisions above |
