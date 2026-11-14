# KPI Snapshot — Week 7 — Embeddings, chunkers and Qdrant

> Drafted by Claude Code from the run results — review and reword the analysis before relying on it.
> Numbers from `scripts/compute_kpis.py` over `data/answers.db` (`rag_runs`, `eval_runs`). Decisions: ADR 0003.

**Date:** 14/11/2026 · **Run:** `wk7-qdrant` · **Store:** Qdrant Cloud, `capstone_chunks` (5,228 points, 1,536 dims,
cosine, HNSW m=16 / ef_construct=100, search hnsw_ef=256) · **Embedder:** text-embedding-3-small ·
**Chunker:** sentence-aware ≤ 500 characters · top-3 · gpt-4o-mini + prompt v2 · judge rubric v2 (unchanged)

## The locked 8-row snapshot

| KPI                     | W7 (`wk7-qdrant`)        | W6 (`wk6-rag-medium`)   | How measured                                      | Notes |
|-------------------------|--------------------------|-------------------------|---------------------------------------------------|-------|
| Task success rate       | not re-graded            | 9 Y + 8 Partial + 3 N   | Blind eyeball (W6 only)                            | Re-grade at the next human review |
| Grounded response rate  | **10 / 17** (5 partial)  | 11 / 17 (6 partial)     | gpt-4o: answer vs its own passages                | Within noise |
| Retrieval hit rate      | **17 / 18** doc · **15 / 18** page | 17 / 18 · 14 / 18 | Expected source in top-3                          | Page +1 from the sentence-aware chunker |
| Cost / query            | **$0.00017**             | $0.00018                | Chat + query embedding                            | Shorter passages |
| Latency p50 / p95       | **3.13 s / 3.91 s**      | 2.81 s / 3.52 s         | Per question, in-process                          | ~0.1 s Qdrant hop; the rest is run-to-run variation |
| Tool / function success | N/A                      | N/A                     | not applicable yet (W11+)                         | |
| Escalation rate         | N/A                      | N/A                     | not applicable yet (W13+)                         | |
| Stakeholder NPS         | N/A                      | N/A                     | not applicable yet                                | |

Answer accuracy (judge, 1–4): **2.70** on Qdrant (W6 baseline 2.55; repeat 2.35). Refusals: 2/2 correct, 1/18
unnecessary (unchanged).

## The embedder × chunker grid

All cells: same 20 questions, harness, judge and prompt; only the embedder or chunker changes.

| Embedder × chunker | Chunks | Doc hit | Page hit | Accuracy | Fully supported | Unneeded refusals | Cost / q | p50 |
|---|---|---|---|---|---|---|---|---|
| 3-small × fixed 500/50 (W6 baseline) | 4,428 | 17/18 | 14/18 | 2.55 · 2.35 | 11/17 · 10/17 | 1/18 | $0.00018 | 2.81 s |
| **3-small × sentence (chosen)** | 5,228 | 17/18 | **15/18** | 2.55 | 9/17 | 1/18 | $0.00017 | 3.38 s |
| 3-large × fixed | 4,428 | 17/18 | 15/18 | 2.50 | 10/17 | 1/18 | $0.00018 | 3.46 s |
| 3-large × sentence | 5,228 | 17/18 | 15/18 | 2.70 · 2.45 | 10/17 · 11/17 | 1/18 | $0.00017 | 3.46 s |
| local MiniLM × fixed | 4,428 | 17/18 | 12/18 | 2.35 | 8/15 | 3/18 | $0.00018 | 2.75 s |
| local MiniLM × sentence | 5,228 | 17/18 | 11/18 | 2.00 | 6/17 | 1/18 | $0.00017 | 2.93 s |

Index build: 3-small $0.008 · 3-large $0.050–0.055 · local $0 (≈45 s on this Mac's CPU, 384 dims, 4× smaller).

**Reading it:**
- **Null finding on documents.** Every cell finds the right document 17/18 times, with the same g008 miss: the
  embedder and chunker are not the bottleneck for that. (The deck: a flat grid is a real finding.)
- **Noise is bigger than W6 measured.** Repeating a cell moved accuracy 0.20–0.25, and identical retrieval on
  NumPy vs Qdrant scored 2.55 vs 2.70. Retrieval is deterministic (page hits repeat exactly); generation and the
  judge are not. Gaps under ~0.25 are not evidence.
- **3-large: no measurable gain.** Mean of two runs 2.58 vs the baseline's 2.45 (+0.13, inside the noise), at
  6.5× the embedding price.
- **Sentence-aware chunking: a small, real retrieval gain.** Page hit 15/18 vs 14/18, repeated in every run with
  both OpenAI models, at equal accuracy and slightly lower cost.
- **Local MiniLM: clearly worse here.** Page hit 11–12/18, accuracy 2.00–2.35, fewer supported answers. Free and
  private, but this corpus is public, so privacy doesn't buy anything yet.
- **Winner (deck rule: lowest cost within 1–2 points of the best):** 3-small + sentence-aware.

## Migration to Qdrant

| Check | Result |
|---|---|
| Points copied (no re-embedding, $0) | 5,228 (`capstone_chunks`) · 4,428 (`capstone_w6_baseline`) |
| Parity: same top-3 as NumPy for every golden question | **20/20** on both collections (with hnsw_ef=256) |
| Parity at Qdrant's default search effort | 20/20 and **19/20**: HNSW missed g019's true top-2 (exact search matched) |
| Full eval on Qdrant vs NumPy, same index | Same chunks retrieved for 20/20 questions |
| Median Qdrant query (network-bound) | ~106 ms at every hnsw_ef tried; exact 108 ms |

### Operational deltas (the Growth Guide's "real W7 win")

| Property | W6 (NumPy) | W7 (Qdrant) |
|---|---|---|
| Persistence | `.npy` + `.json` files, git-ignored | Qdrant-managed (Cloud) |
| Start-up | Load every vector into memory | Connect; nothing to load |
| Search | Linear scan (~1 ms at this size) | HNSW, ~106 ms including the network |
| Filtering | none | payload ready for W8 metadata filters |
| Scale ceiling | RAM-bound | millions of vectors |

## Inline citations on the /ask stream (W6 carry-over)

| Stream path | Passage named in the answer | Fully supported | Unneeded refusals | Accuracy |
|---|---|---|---|---|
| W6 (`wk6-rag-medium-stream`) | 10 / 20 | 10 / 15 | 3 / 18 | 2.45 |
| W7, same index (`wk7-stream-inline`) | **15 / 20** | 11 / 15 | 3 / 18 | 2.50 |
| W7 default on Qdrant (`wk7-qdrant-stream`) | **16 / 20** | 11 / 16 | 2 / 18 | 2.25 |

One instruction ("after each fact, cite the id … in square brackets") lifted named passages from half to
three-quarters of stream answers. Unnecessary refusals barely moved: that's a prompt or retrieval problem for later.
Seen in the UI (`docs/kpi/wk7-screenshots/`): g004 now names two of the four dimensions with an inline citation;
g001 (FEAT) is still declined although three FEAT passages were retrieved: the unnecessary-refusal weakness remains.

## Track A (concept notebooks, Qdrant Cloud)

Both ran end to end against Qdrant Cloud (14/14 and 16/16 code cells, 0 errors). Highlights: 3-large separated
same / related / distant pairs about as well as 3-small; categories clustered without labels; HNSW default vs
tuned and full vs int8-quantized returned identical top-3 at 10 vectors; the dot-product "silent bug" ranked a 3×
scaled ant second for an ocean question while cosine was unaffected; the pets question returned cat, dog and
**sparrow** (the guide expects gecko).

## Practice activity — local embeddings

Done as two grid cells (above). Verdict: on this public corpus, MiniLM's quality loss (page hit −2 to −3, accuracy
−0.2 to −0.5) isn't worth it; it would be the choice for a confidential corpus that must not leave the machine.

## Top 3 observations

1. **The grid is flat on finding documents:** later weeks' levers (W8 filters, W9 hybrid + rerank) are where gains are.
2. **Measurement noise is ±0.2–0.25 with retrieval.** Single runs can't settle small differences; repeat runs or a
   larger golden set are needed (ADR 0003 open question 2).
3. **HNSW's approximation showed up on a real query (g019).** A query-time setting fixed it at no latency cost.

## Method and reproducibility

```bash
python scripts/build_index.py --chunker sentence --out data/index/small-sentence          # also --model text-embedding-3-large / local:minilm
python scripts/run_rag_eval.py --label wk7-small-sentence --condition rag --index data/index/small-sentence
python scripts/migrate_to_qdrant.py --index data/index/small-sentence --collection capstone_chunks
python scripts/run_rag_eval.py --label wk7-qdrant --condition rag --index qdrant:capstone_chunks
python scripts/run_rag_eval.py --label wk7-qdrant-stream --condition rag-stream --index qdrant:capstone_chunks
python scripts/compute_kpis.py --label wk6-rag-medium --label wk7-small-sentence --label wk7-qdrant
```

Console output of every build and run: `docs/kpi/wk7-eval-console.txt`. **Spend for Week 7:** about $1.27
(index builds $0.12; answers + refusal/citation judges $0.42; accuracy judge $0.72; notebooks ~$0.01).
