# ADR-0001a: Stakeholder Map — Singapore AI & Data Governance Assistant

**Capstone:** Grounded Q&A over Singapore AI and data governance frameworks (IMDA, PDPC, MAS)
**Author:** Bhanu Dabral · **Date:** 18/10/2026 · **Status:** Locked (M1)

> The time figures in section 3 are a working estimate, not a measurement.

---

## 1. Primary user — who exactly?

**Compliance and risk analysts at a Singapore financial institution** who, while
reviewing a new AI use case (for example a credit-scoring or customer-chatbot
model), need to check what MAS, PDPC and IMDA expect on a specific point —
fairness, explainability, consent, human oversight — and cite the source in
their review notes.

Why this user fits the repo as built: ADR 0001 says the assistant serves
"practitioners who need a quick, sourced answer"; 9 of the 15 corpus documents
are MAS or MAS-consortium publications aimed at financial institutions; and
the 20 capstone questions are the kind of point lookups such a review needs.

## 2. Secondary stakeholders

| Stakeholder | Type | What they care about |
|---|---|---|
| Head of Compliance | Sponsor | Faster, consistent reviews; no regulatory misstatements |
| Legal / Compliance sign-off | Gatekeeper | The tool never gives legal advice (ADR 0001 decision boundary); every answer is traceable to a named framework |
| IT Security / Data Protection Officer | Gatekeeper | No confidential data leaves the firm; only public documents in the corpus; API keys handled safely |
| Model / AI governance team | Augmented | Fewer repeat "what does the framework say about X?" questions; time back for actual assessments |
| Business teams proposing AI use cases | Augmented (indirect) | Quicker review turnaround |

## 3. Before-AI workflow — how is this solved today?

Known from the repo: the relevant guidance is spread over **15 public documents,
874 pages** (`data/corpus/SOURCES.md`), from three regulators, several revised
in 2026. Answering one question means finding the right document, then the
right section, then reading it.

**Working estimate (not yet measured):** ~20–30 minutes per question (find the
document, search it, read the section, write the citation); ~10 questions per
use-case review; ~4 reviews a month ⇒ **~15–20 hours per analyst per month**.
To validate before DR #2: time one analyst on 5 real questions.

## 4. Desired after-state

The analyst types the question and gets a **2–4 sentence answer naming the
framework and section** (ADR 0001 outputs) in seconds, checks it against the
cited source, and pastes the citation into the review. When the corpus does not
cover the question, the assistant **says so and points to the right
publication** instead of guessing — the failure that motivated the capstone
(plain `gpt-4o-mini` invented a fifth FEAT principle, `docs/runs/02-mas-feat-principles.txt`).

**Target:** under 30 seconds to a checkable answer for ~80% of questions.

## 5. Top 3 sponsor metrics

All three are measurable with what the repo already has. M1 values come from
eval-run-003 (`docs/eval-run-003.md`) and the W4 stress test.

| # | Metric | How it is measured | M1 value | Target (W12 / DR #2) |
|---|---|---|---|---|
| 1 | **Answer accuracy** on the 20-entry golden set | `scripts/run_eval.py`, gpt-4o judge, avg accuracy (1–4) | 1.65 (eval-run-003: rubric v2 + prompt v2) | **≥ 3.5** |
| 2 | **Honest refusals** on out-of-scope questions | Edge entries (g019, g020) scoring ≥ 3 on groundedness, i.e. the assistant declines instead of inventing | 1 / 2 (eval-run-003 with prompt v2: g020 declined, g019 still quoted a fine) | **2 / 2** |
| 3 | **Time and cost per answer** | p95 latency from `scripts/stress_test.py`; cost from `response.usage` | p95 8.55 s; ~$0.0001 per answer (W4) | **p95 < 10 s, ≤ $0.01** |

These three stay as the sponsor metrics for M1. A business metric (e.g. hours
saved per review) can replace one later, once the time estimate in section 3
has been measured.
