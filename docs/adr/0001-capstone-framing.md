# ADR-0001: Capstone Framing — Singapore AI & Data Governance Assistant

- **Status:** v1 (Locked) at M1 — DR #1 held; feedback recorded (reviewer score 18/20, section 10)
- **Date:** 2026-10-12 (v0 draft) · 2026-10-18 (v1) · 2026-11-08 (DR #1 feedback)
- **Author:** Bhanu Dabral

> Sections 1–3 and 7 are the W1 text, unchanged. From here on this file changes only through
> the change log (Section 11).

## 1. Context

Singapore's AI and data governance guidance is spread across separate IMDA and MAS publications, so answering a simple question such as "what does the regulator expect on fairness?" means reading several long documents. This capstone builds a grounded Q&A assistant over a small set (5–20) of those public framework documents, for practitioners who need a quick, sourced answer. An ungrounded model is not good enough here: in `docs/runs/02-mas-feat-principles.txt` plain `gpt-4o-mini` listed five FEAT principles and invented "Security", when FEAT has four (Fairness, Ethics, Accountability, Transparency).

## 2. Locked use case

From the Stakeholder Map (`docs/adr/0001-stakeholder-map.md`):
**Compliance and risk analysts at a Singapore financial institution** who, while reviewing
a new AI use case, need a quick, sourced answer on what MAS, PDPC or IMDA expect on a specific
point (fairness, explainability, consent, human oversight). Sponsor: Head of Compliance.
Corpus: 15 public IMDA / PDPC / AI Verify Foundation / MAS documents, 874 pages
(`data/corpus/SOURCES.md`).

## 3. Decision — Solution Framing Canvas and architecture

| Box | Your answer |
|-----|-------------|
| **Inputs** | A natural-language question of one or two sentences about Singapore AI or data governance, e.g. "What does MAS expect on explainability of AI models?". |
| **Outputs** | A 2–4 sentence plain-English answer plus citations naming the source framework and section it was drawn from. |
| **Tools** | `gpt-4o-mini` for generation, and a retriever over the chunked IMDA and MAS documents (vector store to be chosen in W7). |
| **Memory** | None across calls in v1; every question is answered fresh with no conversation history. |
| **Autonomy level** | Q&A app, between Chatbot and Workflow: it retrieves and answers, and takes no actions. |
| **Decision boundaries** | It may answer only when retrieval finds supporting passages in the corpus; otherwise it says it does not know and points the user to the original IMDA or MAS publication, and it never gives legal or compliance advice. |

**Architecture at M1** (what exists in the repo today; retrieval arrives in W6):

```
Streamlit UI (ui/app.py) ──HTTP──▶ FastAPI (api/main.py)  — contract: ADR 0002, schema_version v1
                                     ├─ POST /ask          → stream_answer()   real token stream
                                     ├─ POST /ask_batched  → ask_llm()         tool-calling → Answer
                                     ├─ GET  /health, /metrics
                                     └─ tiktoken guard: > 2,000 tokens → 422 before any LLM call
                                   src/pipeline/llm.py ──▶ OpenAI gpt-4o-mini (optional versioned system prompt)
                                   SQLite data/answers.db: answers (every /ask_batched) + eval_runs (judge verdicts)
Eval harness (W5): data/golden_set.jsonl → scripts/run_eval.py → judge gpt-4o → eval_runs
```

## 4. Decisions locked at M1

| Decision | Choice | Evidence |
|---|---|---|
| Generation model | `gpt-4o-mini` | W4: 18–20× cheaper than gpt-4o; gpt-4o still wrong on 4 of 7 graded questions (`docs/lab4-model-comparison.md`) |
| Cost budget | ≤ $0.01 per answer | Measured ~$0.0001 per answer (eval-run-003: candidate $0.0020 for 20) |
| API contract | `/ask`, `/ask_batched`, `/health`; `Answer` with `schema_version` "v1" | ADR 0002; unchanged through W4 and W5 |
| Versioning rule | additive optional fields = no bump; remove / rename / retype = bump | ADR 0002 |
| System prompt | **v2** (`data/prompt-v2.txt`, set via `PIPELINE_SYSTEM_PROMPT_FILE` in `.env`) | Pairwise 001: v2 8 wins, v1 1, tie 4, ambiguous 7; eval-run-003 |
| Judge | `gpt-4o`, rubric in `src/eval/judge.py`, temperature 0 | Rubric v2 after blind calibration: exact 57%, within-1 100% (`docs/judge-calibration.md`, `docs/eval-run-002.md`) |
| Golden set | 20 entries, 14 / 4 / 2 | `data/golden_set.jsonl`, `docs/golden-set-notes.md` |
| Local model (Ollama) | not used in production | W4 activity: free but 7× slower, weaker structure compliance |
| Phase 2 comparison design | eval-run-003 stays the baseline. Retrieval is compared with two controls: repeated no-retrieval runs and an oracle-evidence condition (the cited source passages given to the model). Every run reports accuracy plus citation support, retrieval success, correct refusals and unnecessary refusals | DR #1 feedback (section 10): a single no-retrieval run can't separate a retrieval gain from run-to-run noise (±0.2), and the oracle condition shows the ceiling retrieval can reach |

## 5. Sponsor KPIs

| # | KPI | Measured by | M1 value | Target at W12 (DR #2) |
|---|---|---|---|---|
| 1 | Answer accuracy on the golden set | `run_eval.py`, avg accuracy 1–4 | **1.65** (eval-run-003, rubric v2 + prompt v2: the forward baseline) | **≥ 3.5** |
| 2 | Honest refusals on out-of-scope questions | edge entries g019–g020 with groundedness ≥ 3 | **1 / 2** (eval-run-003, prompt v2: g020 declined, g019 still quoted a fine) | **2 / 2** |
| 3 | Latency and cost per answer | `stress_test.py` p95; `response.usage` | p95 4.22 s, p50 2.09 s (40 requests, 3 concurrent, `docs/runs/latency/stress-2026-11-08-40x3.json`); ~$0.0001 | **p95 < 10 s, ≤ $0.01** |

## 6. Evaluation baseline (eval-run-003, the forward baseline)

```
n 20 · avg accuracy 1.65 · avg groundedness 1.95 · avg format 3.40
accuracy 4 / 3 / 2 / 1 : 1 / 1 / 8 / 10 · judge gpt-4o, rubric v2 · candidate gpt-4o-mini, prompt v2, no retrieval
```

The baseline is low because the questions need facts from specific 2024–2026
documents and the app has no retrieval: the model invents plausible lists
(`docs/eval-run-003.md`). This is the "before" number for every Phase 2 change.
Single-run differences of about ±0.2 are noise (`docs/eval-run-002.md`).

Historical runs, kept for the record and **not** comparable with eval-run-003 (different rubric,
prompt or ideal answers): eval-run-001 (rubric v1, no system prompt: 1.65 / 1.70 / 3.40) and
eval-run-002 (rubric v2, no system prompt: 1.40 / 1.50 / 3.45).

## 7. Consequences

- **Positive:**
  - Answers are tied to named source passages, so a reader can check them against the framework itself.
  - An honest "I don't know" replaces confident guesses like the invented fifth FEAT principle.
  - A small, public corpus keeps the build reviewable by the cohort and free of confidential data.
- **Negative / risks:**
  - The corpus goes stale when IMDA or MAS revise a framework, so documents need a recorded version and date.
  - A wrong or misattributed citation in a regulatory domain costs more trust than a missing answer.
  - No memory means follow-up questions lose the context of the previous one.
- **Things we'll re-visit:** the retrieval-confidence threshold for answering versus declining (W12), and multi-turn memory (W14).

## 8. Risks found at M1

| Risk | Seen in | Mitigation |
|---|---|---|
| Confident invented lists | eval-run-003 (10 of 20 scored accuracy 1) | Retrieval (W6+); v2 refusal prompt for out-of-scope |
| Self-reported confidence is meaningless | W4: 0.85–0.95 on wrong answers | Don't show it to users until calibrated against eval |
| Judge errors and position bias | pairwise 001: 4 order flips; one judge factual error | Always judge both orders; blind calibration (take-home) |
| Self-critique can't add missing facts | Critic-Creator g015: flat 2.33 | Re-test after retrieval |

## 9. Open questions

1. What evidence is sufficient to answer rather than decline (W12)? Calibrate the threshold on evidence sufficiency, counting both correct refusals and unnecessary refusals, not on accuracy alone.
2. Is a judge with 57% exact / 100% within-1 agreement good enough for W6 retrieval decisions, or do I need a second judge? The 10 calibration entries were also used to sharpen rubric v2, so validate it again on fresh human-scored examples. (`docs/judge-calibration.md`)
3. Does the assistant actually save analysts time? The 20–30 minutes per question is a working estimate (Stakeholder Map §3); time one analyst on 5 real questions before DR #2. *(From DR #1.)*

## 10. DR #1 defence

DR #1 held 18/10/2026; written feedback recorded 08/11/2026. **Reviewer score 18/20:** Problem
clarity 4, Architecture 4, Evidence 3, Decisions 4, Defensibility 3 ("Strong M1 work, with clear
evidence gaps to close").

| Challenge | Response | ADR change |
|---|---|---|
| The time-saving assumptions need validation with a real analyst (Problem clarity) | Agreed: the 20–30 minutes is labelled a working estimate. Time one analyst on 5 real questions before DR #2. | §9 Q3 added |
| No raw evidence for the 8.55 s p95 (Evidence) | Correct: the W4 run was only printed, and with 10 requests its "p95" was the slowest request. `stress_test.py` now saves configuration and every request's timing; re-run at 40 requests × 3 concurrent: p95 4.22 s. | §5 KPI 3; `docs/runs/latency/` |
| The live demo was not observed (Evidence) | The demo runs as in README (Week 3); eval-run-003's answers are stored in `data/answers.db` (`eval_runs`). Demo live at DR #2. | None |
| No evidence of updating the ADR live (Defensibility) | Updated after the review instead (commits `d2e04f7`, `8587fb8` and this one). Commit a live ADR update during DR #2. | §10, §11 |
| The retrieval comparison must be defensible | Accepted: retrieval vs repeated no-retrieval and oracle-evidence controls, with citation support, retrieval success, correct and unnecessary refusals reported alongside accuracy. | §4 row added; §9 Q1–Q2 |
| Run 003 is not the consistent baseline across the ADR | Fixed: eval-run-003 is the forward baseline in §4–§6 and §8; runs 001 and 002 are labelled historical. | §4–§6, §8 |

**To sharpen before DR #2** (the reviewer's two points, now W6–W12 goals):

1. **Make the retrieval comparison defensible.** Run the three conditions (retrieval, repeated
   no-retrieval, oracle evidence); independently review additional golden answers; report citation
   support, retrieval success, correct refusals and unnecessary refusals alongside average accuracy;
   calibrate refusal on evidence sufficiency; validate the judge on fresh human-scored examples.
2. **Close the documentation and reproducibility gaps.** Keep eval-run-003 the consistent forward
   baseline; retain raw latency results and configuration (done 08/11/2026); record peer challenges
   and responses (this section).

## 11. Change log

| Date | Version | Change |
|---|---|---|
| 2026-10-12 | v0 draft | W1: context, Solution Framing Canvas, consequences |
| 2026-10-17 | v0 (+ADR 0002) | W4: model choice, cost budget, schema versioning rule — recorded in ADR 0002 |
| 2026-10-18 | v1 (Locked) | W5: locked use case, M1 decisions, KPIs, eval baseline, risks, open questions |
| 2026-10-18 | v1 (+eval) | Judge rubric v2 after blind calibration; eval-run-002 (accuracy 1.40, rubric v2, no system prompt) |
| 2026-10-18 | v1 (+prompt) | Prompt v2 shipped; eval-run-003 (accuracy 1.65, groundedness 1.95, rubric v2 + prompt v2) is the W6 comparison point |
| 2026-11-08 | v1 (+DR #1) | DR #1 feedback recorded (18/20). eval-run-003 the forward baseline throughout; KPI 3 re-measured with raw results kept (p95 4.22 s); Phase 2 comparison design added to §4; §9 updated. No locked decision changed, so no eval re-run was needed |
| 2026-11-14 | v1 (+W6) | Naive RAG live on /ask and /ask_batched (section 12). Baseline KPIs from wk6-rag-medium against the DR #1 controls; top 3 limits recorded; both API paths measured (wk6-rag-medium-stream) |
| 2026-11-14 | v1 (+W7) | Retrieval stack decided in ADR 0003 (draft): text-embedding-3-small, sentence-aware chunker, Qdrant Cloud (cosine, HNSW, hnsw_ef 256). Migration parity 20/20; KPIs in docs/kpi/wk7-snapshot.md |

## 12. W6 — Naive RAG live



**Decision:** naive RAG is now the default answer path. With `PIPELINE_RAG_INDEX` set, `/ask_batched` and `/ask`
retrieve the top-3 chunks (cosine over `text-embedding-3-small` vectors) from the 15-document corpus and answer
from them. Chunking: sliding window, 500 characters, 50 overlap (4,428 chunks; SAFR v1.0 excluded). The answer
path is otherwise unchanged: `gpt-4o-mini`, prompt v2, tool-calling `Answer` (schema v1, ADR 0002). `sources` now
holds the chunk ids the model cited, filtered to those actually retrieved.

**Why naive first:** Phase 2 changes one box at a time, and every later change is measured against this.
Long-context is not an option (the corpus is ~520k tokens, 4× gpt-4o-mini's window); fine-tuning can't cite.

**Baseline KPIs** (`docs/kpi/wk6-snapshot.md`, label `wk6-rag-medium`):

| KPI (§5) | M1 (eval-run-003, no retrieval) | **W6 (naive RAG)** | Oracle ceiling | Target W12 |
|---|---|---|---|---|
| 1 · Accuracy (judge, 1–4) | 1.65 (three runs: 1.55–1.75) | **2.55** | 3.25 | ≥ 3.5 |
| 2 · Honest refusals (g019, g020) | 1 / 2 (varies by run) | **2 / 2** | 2 / 2 | 2 / 2 |
| 3 · Latency p95 · cost / answer | 4.22 s (stress test) · ~$0.0001 | **3.52 s · $0.00018** | 5.59 s · $0.00024 | < 10 s · ≤ $0.01 |
| Retrieval hit rate (doc · page) | — | **17 / 18 · 14 / 18** | — | — |
| Citation support (full) | — | **11 / 17** | 17 / 18 | — |
| Unnecessary refusals | 0 / 18 | **1 / 18** | 0 / 18 | — |
| Task success (blind eyeball, Bhanu) | — | **9 Y + 8 Partial + 3 N** of 20 | — | — |

Human vs judge on these answers: 15/20 agree; the judge is more lenient than the human on omissions (g005, g012, g018), which updates §9 Q2. KPI 2 met its W12 target already. KPI 1 moved +0.90 against noise of about ±0.1; the oracle shows retrieval
quality, not the model, limits the rest (target ≥ 3.5 is above even the oracle's 3.25 today: revisit in W8 if
the oracle doesn't move with better chunking and a stricter prompt).

**Top 3 limits** (to address W7–W11):
1. **Right document, wrong page** (page hit 14/18): the model then declines although the answer exists (g010)
   or answers from memory despite the instruction (g004, g006). → W7 section-aware chunking; W9 rerank.
2. **Wrong document when documents share vocabulary** (g008: Veritas question, MindForge passages).
   → W9 hybrid search; W10 metadata filters.
3. **Grounding leaks:** 6/17 answers include unsupported claims, and one correct refusal points the user to the
   wrong document (g020). → stricter grounding prompt and citation verification (W11).

**UI path measured too (decided 14/11/2026):** the UI's `/ask` stream answered the same passages differently from
the measured `/ask_batched` (g001 declined 5/5 vs 0/5), so the eval gained a `rag-stream` condition. Stream:
accuracy 2.45 (vs 2.55, within noise), unnecessary refusals 3/18 (vs 1/18), passages named in 10/20 answers (the
grounded prompt asks for `sources`, which a stream lacks). Decision: keep streaming in the UI; report both paths
every week; W7 tries an inline-citation instruction for the stream.

**Chunk-size sweep (Activity A):** document hit rate identical across 300/30, 500/50, 800/80 (17/18); 300/30
finds the cited page more often (16/18) and is cheapest. 500/50 stays the baseline (the only profile judged on
quality); 300/30 is the W7 challenger.

**Status:** live in the demo API. Not ready for analysts: one in three answers is not fully supported by its
passages, and three answerable questions still fail on retrieval.

## 13. W7 — Retrieval stack (see ADR 0003)

The retrieval layer is now decided in its own record, `docs/adr/0003-retrieval-architecture.md` (draft, to lock at
M2): text-embedding-3-small, a sentence-aware chunker (≤ 500 characters) and Qdrant Cloud (`capstone_chunks`,
cosine, HNSW, hnsw_ef = 256), chosen from a measured grid of 3 embedders × 2 chunkers. The app's behaviour and
contract are unchanged; the W6 NumPy index remains as the reference backend.

