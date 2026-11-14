# KPI Snapshot — Week 6 — Naive RAG baseline

> Drafted by Claude Code from the run results — review and reword the analysis before relying on it.
> Numbers are produced by `scripts/compute_kpis.py` from `data/answers.db` (tables `rag_runs`, `eval_runs`).

**Date:** 14/11/2026 · **Run:** `wk6-rag-medium` · **Corpus:** 15 documents, 874 pages (SAFR v1.0 excluded),
4,428 chunks · **Golden set:** 20 questions (18 answerable, 2 out of scope)
**System:** sliding-window chunks 500/50 · `text-embedding-3-small` · top-3 cosine · `gpt-4o-mini` + prompt v2 ·
tool-calling `Answer` (schema v1)

## The locked 8-row snapshot

| KPI                     | Value                  | How measured                                          | Notes |
|-------------------------|------------------------|-------------------------------------------------------|-------|
| Task success rate       | **9 / 20** Y (+ 8 Partial, 3 N) | Eyeball Y / N / Partial, blind, by Bhanu (`docs/kpi/wk6-task-success.csv`) | 13 / 20 counting Partial as ½ |
| Grounded response rate  | **11 / 17** fully supported (6 partial) | gpt-4o judges each answer against its own passages | Excludes the 3 answers that declined |
| Retrieval hit rate      | **17 / 18** (doc) · 14 / 18 (page) | Expected source in top-3 (`data/golden_sources.json`) | g008: wrong document |
| Cost / query            | **$0.00018**           | Chat tokens + query embedding, mean of 20             | Index build: $0.0085 once |
| Latency p50 / p95       | **2.81 s / 3.52 s**    | Per question, in-process, nearest-rank                | Mostly the LLM call |
| Tool / function success | N/A                    | not applicable yet (W11+)                             | |
| Escalation rate         | N/A                    | not applicable yet (W13+)                             | |
| Stakeholder NPS         | N/A                    | not applicable yet                                    | |

Against the deck's bands: task success 9/20 fully acceptable is **below acceptable** (≥ 12/20); with Partials as ½ it is 13/20. Hit rate 17/18 is **good** (≥ 18/20 equivalent), cost is **good** (< $0.005),
grounded rate 65% is **below acceptable** (≥ 80%), and p95 3.5 s is **just over acceptable** (< 3 s).

## DR #1 comparison: retrieval against two controls

Same golden set, model, prompt v2 and judge (gpt-4o, rubric v2); only the evidence the model sees changes.

| Measure | No retrieval (eval-run-003 · r2 · r3) | **Retrieval (500/50, K=3)** | Oracle evidence (cited pages) |
|---|---|---|---|
| Accuracy (judge, 1–4) | 1.65 · 1.75 · 1.55 → **1.65 ± 0.10** | **2.55** | **3.25** |
| Groundedness (judge, 1–4) | 1.95 · 2.35 · 2.20 | **2.95** | 3.20 |
| Citation support (full / answered) | N/A (no passages) | **11 / 17** (6 partial) | 17 / 18 (1 partial) |
| Retrieval success (doc · page) | N/A | **17 / 18 · 14 / 18** | by construction |
| Correct refusals (g019, g020) | 1 / 2 · 2 / 2 · 1 / 2 | **2 / 2** | 2 / 2 |
| Unnecessary refusals (of 18) | 0 · 0 · 0 | **1** (g010) | 0 |
| Cost / query | ~$0.0001 | $0.00018 | $0.00024 |
| Latency p50 / p95 | 2.3–2.5 s / 3.1–3.6 s | 2.81 s / 3.52 s | 3.49 s / 5.59 s |

**Reading it:**
- **The gain is real.** Three no-retrieval runs span 1.55–1.75, so run-to-run noise is about ±0.1. Retrieval
  adds +0.90, about nine times the noise.
- **Naive RAG gets 56% of the way to the ceiling.** Perfect evidence reaches 3.25, so (2.55 − 1.65) / (3.25 − 1.65)
  = 0.56. The remaining 0.70 is what better retrieval (W7–W10) can still win.
- **Refusals became reliable.** Without retrieval g019 (EU AI Act fine) flips between declining and quoting a
  fine (2 of 3 runs invented one). With retrieval both out-of-scope questions are declined.
- **But the gain is uneven.** 3 answerable entries still score accuracy 1 with retrieval (g004, g006, g010).
  The oracle lifts all three to 3–4, so those are retrieval failures, not model failures.

## Human grades vs the judge (fresh human-scored examples)

Bhanu graded the 20 `wk6-rag-medium` answers blind (no judge scores shown), 14/11/2026. DR #1 asked for exactly
this: independent review of golden answers, and the judge validated on fresh human-scored examples (ADR §9 Q2).

| Your grade | Count | Entries |
|---|---|---|
| Y | 9 | g001, g002, g007, g008, g009, g011, g014, g015, g019 |
| Partial | 8 | g003, g005, g012, g013, g016, g017, g018, g020 |
| N | 3 | g004, g006, g010 (the three retrieval failures in limit 1) |

Mapping the judge's accuracy as 4–3 = Y, 2 = Partial, 1 = N, the judge agrees on **15 / 20**:

| Entry | Your grade | Judge | Who was stricter |
|---|---|---|---|
| g005 | Partial (action gate omitted) | 3 | You |
| g012 | Partial (qualification missing) | 3 | You |
| g018 | Partial (case-study scope missing) | 3 | You |
| g008 | Y (core purpose correct) | 2 | Judge |
| g020 | Partial (wrong referral source) | 1 | Judge |

**Reading it:** on RAG answers the judge is **more lenient than you on omissions** (3 cases: it gives 3, "mostly
right", where a missing item makes it Partial for you). That differs from the W5 calibration, where the judge was
never more lenient on accuracy. Either the rubric's level 3 needs sharpening for "one required item missing", or
the mapping should treat 3 as Partial for list questions. Not changed in W6 (rubric changes need a re-judge);
recorded for W7 under ADR §9 Q2. The three N grades match the snapshot's limit 1 exactly.

## Activity A — chunk-size sweep

Tested (300/30), (500/50), (800/80) against the same 20 questions. Hit rate, cost and latency only
(the take-home's table); answer quality was judged for the 500/50 run alone.

| Profile | size | overlap | Chunks | Hit rate (doc) | Hit rate (page) | Cost / q | p95 latency | Unnecessary refusals |
|---------|------|---------|--------|----------------|-----------------|----------|-------------|----------------------|
| Small   | 300  | 30      | 7,376  | 17 / 18        | **16 / 18**     | $0.00016 | 3.59 s      | 1 (g006) |
| Medium  | 500  | 50      | 4,428  | 17 / 18        | 14 / 18         | $0.00018 | 3.52 s      | 1 (g010) |
| Large   | 800  | 80      | 2,769  | 17 / 18        | 14 / 18         | $0.00020 | 3.55 s      | 0 |

**Winner: none at the document level; small (300/30) at the page level.** Document hit rate is identical
(17/18, the same g008 miss), so chunk size is not a high-leverage variable for finding the right document in this
corpus. Small finds the cited page more often (16 vs 14) and is the cheapest, because its passages are shorter.
Latency is the same within noise.

**Recommendation:** keep **500/50** as the W6 baseline, because it is the only profile measured on answer quality
and with the controls. Carry **300/30** into W7 as the challenger next to section-aware chunking, judged with the
same harness, since its page-level edge is a hypothesis until its answers are scored.

## Activity B — local embeddings (stretch): skipped

Not run, by choice: `sentence-transformers` needs PyTorch (~1 GB), and W7 covers embedding-model choice formally,
with the same harness. Recorded here so the snapshot stays complete.

## Top 3 limits observed

1. **Right document, wrong page.** Document hit 17/18 but page hit 14/18. When the cited page is missed, the
   model either declines although the corpus has the answer (g010: an unnecessary refusal), or **answers from
   memory despite the instruction** (g004 lists four invented "dimensions"; g006 adds dimensions not in the
   passages). The oracle answers all three correctly. → W7 section-aware chunking, W9 rerank.
2. **Wrong document when vocabularies overlap.** g008 asks about the Veritas Initiative; all three passages come
   from the MindForge Executive Handbook, which also mentions Veritas. → W9 hybrid search, W10 metadata filters.
3. **Grounding leaks.** 6 of 17 answers include claims their passages don't support (g001 adds its own definitions
   of the FEAT principles), and one correct refusal **points to the wrong document** (g020 names the retrieved
   PDPA guidelines, which hold no fines), so the W5 judge scores it accuracy 1. → stricter grounding prompt,
   citation verification (W11).

## The UI path, measured too (`wk6-rag-medium-stream`)

The eval above measures `/ask_batched` (tool-calling `Answer`). The Streamlit UI uses `/ask`, which streams plain
text from the same retrieval, prompt v2 and grounded prompt. A UI screenshot showed g001 (FEAT) declined while the
eval path answered it (5 tries each: stream declined 5/5, tool call 0/5), so the stream path now has its own
condition, `rag-stream`, run through the same harness:

| Measure | `/ask_batched` (tool call) | **`/ask` stream (UI)** |
|---|---|---|
| Accuracy (judge) · groundedness | 2.55 · 2.95 | **2.45** · 2.80 |
| Citation support (full / answered) | 11 / 17 (6 partial) | 10 / 15 (5 partial) |
| Retrieval hit (doc · page) | 17/18 · 14/18 | 17/18 · 14/18 (same retrieval) |
| Correct refusals | 2 / 2 | 2 / 2 |
| Unnecessary refusals | 1 / 18 (g010) | **3 / 18** (g001, g006, g010) |
| Answers naming the passage used | 20 / 20 (`sources` field) | **10 / 20** (inline `[id]` tags) |
| Cost / query · p95 | $0.00018 · 3.52 s | $0.00014 · 3.20 s |

**Reading it:** the two paths are equal on accuracy within the ±0.10 noise, but the stream reads the passages more
literally: it declines three answerable questions where the passages are thin or on the wrong page, against one
for the tool call. The stream's accuracy is also slightly flattered: the judge scored its g010 "I don't know"
accuracy 4 although the corpus answers g010 (a judge error, see ADR §9 Q2). And half the stream answers don't say
which passage they used, because the grounded prompt asks for ids in `sources`, a field only the tool call has.

**Decision (14/11/2026):** keep streaming in the UI and report both paths every week from now on. W7 candidates:
a stream-specific citation instruction (cite `[id]` inline), then re-measure both paths.

## Method and reproducibility

```bash
python scripts/build_index.py --size 500 --overlap 50 --out data/index/medium      # also small (300/30), large (800/80)
python scripts/run_rag_eval.py --label wk6-rag-medium --condition rag --index data/index/medium
python scripts/run_rag_eval.py --label wk6-norag-r2 --condition none --no-support   # and wk6-norag-r3
python scripts/run_rag_eval.py --label wk6-oracle --condition oracle
python scripts/run_rag_eval.py --label wk6-rag-medium-stream --condition rag-stream --index data/index/medium
python scripts/run_rag_eval.py --label wk6-rag-small --condition rag --index data/index/small --no-judge --no-support
python scripts/run_rag_eval.py --label eval-run-003 --import-label                 # refusal check on the W5 answers
python scripts/compute_kpis.py --label eval-run-003 --label wk6-norag-r2 --label wk6-norag-r3 \
                               --label wk6-rag-medium --label wk6-oracle
```

- Every answer, its retrieved and cited chunks, hit, refusal, citation-support verdict, latency and cost are
  stored per question in `rag_runs`; accuracy verdicts in `eval_runs` under the same label. The console output of
  all runs is kept in `docs/kpi/wk6-eval-console.txt`.
- eval-run-003 was imported from its stored W5 answers: refusals were classified, but its latency and per-question
  cost weren't recorded in W5 (its doc gives $0.0020 for 20).
- **Spend for Week 6:** about $0.55 (index builds $0.026; answers and refusal/citation judges $0.16; accuracy judge
  $0.36; the stream-vs-tool check $0.003), plus ~$0.004 for the Track A notebooks.
