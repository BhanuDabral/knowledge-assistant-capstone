# DR #1 — one-pager · Bhanu Dabral

**Capstone:** Singapore AI & Data Governance Assistant · **Repo:** github.com/BhanuDabral/knowledge-assistant-capstone · **M1, 18/10/2026**

## What I built

A Q&A assistant over 15 public Singapore AI and data governance documents
(IMDA, PDPC, MAS; 874 pages). It is for **compliance and risk analysts at a Singapore financial institution**
reviewing new AI use cases, who today spend an estimated **20–30 minutes per question**
finding the right framework and section (a working estimate, not yet measured). Today it
is a FastAPI service (`/ask` streams, `/ask_batched` returns a structured
`Answer` with cost, confidence and `schema_version` v1) with a Streamlit UI,
on `gpt-4o-mini`. **There is no retrieval yet** (that comes in W6), so it
answers from the model's memory.

## What I measured

- **Eval baseline (eval-run-001):** 20-entry golden set (14 happy / 4 harder /
  2 edge, ideal answers cited to source pages), judged by gpt-4o: **accuracy
  1.65, groundedness 1.70, format 3.40** out of 4. The model invents named lists
  (dimensions, roles, offences) it doesn't know.
- **Prompt pairwise:** adding one refusal rule (v2) beat v1 **8 to 1** (4 ties,
  7 order-dependent). It fixed the out-of-scope case (no more invented EU AI Act
  fine) but not in-scope hallucinations.
- **Critic-Creator on g015:** flat at 2.33 for 3 rounds. Self-critique fixed an
  invented framework name but couldn't add missing facts.
- **Cost and latency (W4):** ~$0.0001 per answer (budget $0.01); p95 8.55 s
  under 3-way concurrency.

## Top 3 things I want to discuss

1. **Is a 1.65 baseline the right "before" number?** Or should I add a
   no-retrieval control *and* a docs-in-prompt upper bound, so W6–W8 retrieval
   gains are easier to interpret?
2. **When should the assistant decline?** The v2 prompt only declines when the
   model *knows* it doesn't know. What retrieval signal should trigger "I don't
   know" in W12?
3. **How much should I trust my judge?** Order flips on 4 of 20 pairwise
   questions and one factual error by the judge. Is blind calibration on 10
   entries enough, or do I need a second judge?

## What I'll defend if asked

- **Why gpt-4o-mini?** 18–20× cheaper than gpt-4o (W4), and gpt-4o was still
  wrong on 4 of 7 regulator-specific questions. The gap is grounding, not model
  size.
- **Why this user?** Compliance analysts reviewing AI use cases need sourced answers
  from exactly these documents: 9 of the 15 are MAS publications for financial
  institutions, and a wrong citation costs more than no answer, which is why the
  assistant must decline when the corpus doesn't cover a question.
- **Why only 20 golden entries?** It's the floor for M1. They're built from my
  own W2 questions with cited ideal answers, including a false-premise question
  (g017) and two out-of-scope edges. The plan is to grow to 50 (take-home
  stretch).

## Open questions I'm sitting with

- Scoring 10 answers blind showed the judge is never more lenient than me on accuracy or
  groundedness, so I trust it to flag regressions. But answers change from run to run, so in
  W6–W9 I'll re-run the eval after every retrieval change and compare 20-question averages, not
  single entries.
- **Judge calibration (blind, 10 entries):** exact 50% → 57% and within-1 97% → 100% after one rubric sharpening (v2). Is ±1 agreement good enough for W6 retrieval decisions, or should I add a second judge?
- Which question categories are missing from the golden set (e.g. multi-turn
  follow-ups, questions comparing two regulators)?

## Update after DR #1 (18/10/2026)

- Prompt v2 is now shipped; **eval-run-003** (rubric v2 + prompt v2): accuracy 1.65,
  groundedness 1.95, format 3.40. This is the W6 comparison point (`docs/eval-run-003.md`).
- Correction to "What I measured": with v2 live, g019 **again** quoted an EU AI Act fine in
  eval-run-003, so the refusal rule lowers the risk but doesn't remove it.
- DR #1 feedback: pending.
