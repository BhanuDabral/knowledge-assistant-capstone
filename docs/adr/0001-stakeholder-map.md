# ADR-0001a: Stakeholder Map — Singapore AI & Data Governance Assistant

**Capstone:** Grounded Q&A over Singapore AI and data governance frameworks (IMDA, PDPC, MAS)
**Author:** Bhanu Dabral · **Date:** 18/10/2026 · **Status:** Draft — to be locked at M1

> **Drafted by Claude Code — review and reword.** Facts taken from your repo are
> stated plainly. Anything only you can know is marked **[YOU: …]** with a
> suggestion; replace every marker (`grep -n "\[YOU" docs/adr/0001-stakeholder-map.md`)
> before you commit this as locked.

---

## 1. Primary user — who exactly?

**[YOU: confirm or replace]** Suggested: *compliance and risk analysts at a
Singapore financial institution who, while reviewing a new AI use case (for
example a credit-scoring or customer-chatbot model), need to check what MAS,
PDPC and IMDA expect on a specific point — fairness, explainability, consent,
human oversight — and cite the source in their review notes.*

Why this user fits the repo as built: ADR 0001 says the assistant serves
"practitioners who need a quick, sourced answer"; 9 of the 15 corpus documents
are MAS or MAS-consortium publications aimed at financial institutions; and
your 20 capstone questions are the kind of point lookups such a review needs.

## 2. Secondary stakeholders

| Stakeholder | Type | What they care about |
|---|---|---|
| **[YOU: e.g. Head of Compliance / Chief Risk Officer]** | Sponsor | Faster, consistent reviews; no regulatory misstatements |
| Legal / Compliance sign-off | Gatekeeper | The tool never gives legal advice (ADR 0001 decision boundary); every answer is traceable to a named framework |
| IT Security / Data Protection Officer | Gatekeeper | No confidential data leaves the firm; only public documents in the corpus; API keys handled safely |
| Model / AI governance team | Augmented | Fewer repeat "what does the framework say about X?" questions; time back for actual assessments |
| Business teams proposing AI use cases | Augmented (indirect) | Quicker review turnaround |

## 3. Before-AI workflow — how is this solved today?

Known from the repo: the relevant guidance is spread over **15 public documents,
874 pages** (`data/corpus/SOURCES.md`), from three regulators, several revised
in 2026. Answering one question means finding the right document, then the
right section, then reading it.

**[YOU: put real numbers here]** Suggested shape: *"~20–30 minutes per question
(find the document, search it, read the section, write the citation); ~10
questions per use-case review; ~4 reviews a month ⇒ ~15–20 hours per analyst
per month."* Only use numbers you can defend at DR #1 — your own experience,
or a colleague's estimate you name.

## 4. Desired after-state

The analyst types the question and gets a **2–4 sentence answer naming the
framework and section** (ADR 0001 outputs) in seconds, checks it against the
cited source, and pastes the citation into the review. When the corpus does not
cover the question, the assistant **says so and points to the right
publication** instead of guessing — the failure that motivated the capstone
(plain `gpt-4o-mini` invented a fifth FEAT principle, `docs/runs/02-mas-feat-principles.txt`).

**[YOU: optional]** Add the time target you want, e.g. "under 30 seconds to a
checkable answer for ~80% of questions".

## 5. Top 3 sponsor metrics

All three are measurable with what the repo already has. The M1 column is
filled from the W4/W5 runs once `docs/eval-run-001.md` exists.

| # | Metric | How it is measured | M1 value | Target (W12 / DR #2) |
|---|---|---|---|---|
| 1 | **Answer accuracy** on the 20-entry golden set | `scripts/run_eval.py`, gpt-4o judge, avg accuracy (1–4) | see eval-run-001 | **[YOU: e.g. ≥ 3.5]** |
| 2 | **Honest refusals** on out-of-scope questions | Edge entries (g019, g020) scoring ≥ 3 on groundedness, i.e. the assistant declines instead of inventing | see eval-run-001 | **[YOU: e.g. 2 / 2]** |
| 3 | **Time and cost per answer** | p95 latency from `scripts/stress_test.py`; cost from `response.usage` | p95 8.55 s; ~$0.0001 per answer (W4) | **[YOU: e.g. p95 < 10 s, ≤ $0.01]** |

**[YOU: decide]** If your sponsor would rather see a business metric (e.g.
"hours saved per review"), swap one in — but it needs a measurement plan
(how you'd count the hours), or reviewers will call it a vibe.
