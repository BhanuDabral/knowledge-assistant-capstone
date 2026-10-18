# ADR-0001: Capstone Framing — Singapore AI & Data Governance Assistant

- **Status:** v1 (Locked) at M1 — *to be defended at DR #1*
- **Date:** 2026-10-12 (v0 draft) · 2026-10-18 (v1)
- **Author:** Bhanu Dabral

> **W5 extension drafted by Claude Code — review and reword.** Sections 1–3 and 7
> are your W1 text, unchanged. Sections 4–6, 8–9 and 11 were added from the W4 and
> W5 results. Replace every **[YOU: …]** before DR #1
> (`grep -n "\[YOU" docs/adr/0001-capstone-framing.md`). After DR #1, this file
> changes only through the change log (Section 11).

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
| Cost budget | ≤ $0.01 per answer | Measured ~$0.0001 per answer (eval-run-001: $0.001982 for 20) |
| API contract | `/ask`, `/ask_batched`, `/health`; `Answer` with `schema_version` "v1" | ADR 0002; unchanged through W4 and W5 |
| Versioning rule | additive optional fields = no bump; remove / rename / retype = bump | ADR 0002 |
| System prompt | **[YOU: v2 or v1]** — draft: `data/prompt-v2.txt` | Pairwise 001: v2 8 wins, v1 1, tie 4, ambiguous 7 |
| Judge | `gpt-4o`, rubric in `src/eval/judge.py`, temperature 0 | Rubric v2 after blind calibration: exact 57%, within-1 100% (`docs/judge-calibration.md`, `docs/eval-run-002.md`) |
| Golden set | 20 entries, 14 / 4 / 2 | `data/golden_set.jsonl`, `docs/golden-set-notes.md` |
| Local model (Ollama) | not used in production | W4 activity: free but 7× slower, weaker structure compliance |

## 5. Sponsor KPIs

| # | KPI | Measured by | M1 value | Target at W12 (DR #2) |
|---|---|---|---|---|
| 1 | Answer accuracy on the golden set | `run_eval.py`, avg accuracy 1–4 | **1.65** (rubric v1) · **1.40** (rubric v2, eval-run-002: compare W6 against this) | **≥ 3.5** |
| 2 | Honest refusals on out-of-scope questions | edge entries g019–g020 with groundedness ≥ 3 | **1 / 2** without a system prompt (prompt v2 declined both in pairwise 001, not yet scored) | **2 / 2** |
| 3 | Latency and cost per answer | `stress_test.py` p95; `response.usage` | p95 8.55 s; ~$0.0001 | **p95 < 10 s, ≤ $0.01** |

## 6. Evaluation baseline (eval-run-001)

```
n 20 · avg accuracy 1.65 · avg groundedness 1.70 · avg format 3.40
accuracy 4 / 3 / 2 / 1 : 2 / 1 / 5 / 12 · judge gpt-4o · candidate gpt-4o-mini, no retrieval
```

The baseline is low because the questions need facts from specific 2024–2026
documents and the app has no retrieval: the model invents plausible lists
(`docs/eval-run-001.md`). This is the "before" number for every Phase 2 change.

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
| Confident invented lists | eval-run-001 (12 of 20 scored accuracy 1) | Retrieval (W6+); v2 refusal prompt for out-of-scope |
| Self-reported confidence is meaningless | W4: 0.85–0.95 on wrong answers | Don't show it to users until calibrated against eval |
| Judge errors and position bias | pairwise 001: 4 order flips; one judge factual error | Always judge both orders; blind calibration (take-home) |
| Self-critique can't add missing facts | Critic-Creator g015: flat 2.33 | Re-test after retrieval |

## 9. Open questions

1. What retrieval-confidence threshold should switch the app from answering to declining (W12)?
2. Is a judge with 57% exact / 100% within-1 agreement good enough for W6 retrieval decisions, or do I need a second judge? (`docs/judge-calibration.md`)
3. **[YOU: a question from your peer dry-run]**

## 10. DR #1 defence

*(Fill in live during the DR #1 slot: the challenge, your answer, and any ADR change agreed.)*

| Challenge | Response | ADR change |
|---|---|---|
| | | |

## 11. Change log

| Date | Version | Change |
|---|---|---|
| 2026-10-12 | v0 draft | W1: context, Solution Framing Canvas, consequences |
| 2026-10-17 | v0 (+ADR 0002) | W4: model choice, cost budget, schema versioning rule — recorded in ADR 0002 |
| 2026-10-18 | v1 (Locked) | W5: locked use case, M1 decisions, KPIs, eval baseline, risks, open questions |
| 2026-10-18 | v1 (+eval) | Judge rubric v2 after blind calibration; eval-run-002 (accuracy 1.40, rubric v2) becomes the comparison point for W6 |
