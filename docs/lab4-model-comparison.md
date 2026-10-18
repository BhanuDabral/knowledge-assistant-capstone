# Lab 4 — Model comparison: gpt-4o-mini vs gpt-4o

**Cohort member:** Bhanu Dabral
**Date:** 17/10/2026

## Numbers (`scripts/compare_models.py`, real OpenAI API, cost from `response.usage`)

**Lab set: the 10 W4 questions** (`data/w4_questions.csv` → `data/answers.db`)

```
Model            n    Total $     Avg $/q     Avg words  Avg confidence
-----------------------------------------------------------------------
gpt-4o-mini     10    0.000724    0.000072      63          0.90
gpt-4o          10    0.014793    0.001479      89          0.92
```

> gpt-4o cost **20.4×** more than gpt-4o-mini on the same questions. One run of 10 took about 14 s (mini) and 15 s (gpt-4o), sequentially.

**Capstone set: the 20 IMDA / PDPC / MAS questions** (`data/capstone_questions.csv` → `data/answers_capstone.db`, no retrieval yet)

```
Model            n    Total $     Avg $/q     Avg confidence
------------------------------------------------------------
gpt-4o-mini     20    0.001888    0.000094      0.90
gpt-4o          20    0.034452    0.001723      0.89
```

> gpt-4o cost **18.2×** more.

**Data note.** Two lab questions (L1 and L6) contain a comma that the course CSV did not quote, so they were first asked cut short ("What is Retrieval-Augmented Generation" without ", in two sentences?"). The CSV was fixed, those 4 rows deleted, and both questions re-asked in full. The table above is all 10 full questions.

## Graded against source documents (capstone questions with a confirmed source page)

| Q | What the source says | gpt-4o-mini | gpt-4o |
|---|---|---|---|
| 1 | FEAT = Fairness, Ethics, Accountability, Transparency | ✅ | ✅ |
| 4 | The four Research Exception conditions (PDPA Key Concepts p74) | ❌ ~1 of 4 | ⚠️ 2 of 4 |
| 8 | The nine GenAI framework dimensions (MGF GenAI p2) | ❌ invents nine | ❌ vague, no list |
| 11 | Part 9B: knowing or reckless disclosure, wrongful use, re-identification (p9) | ⚠️ | ⚠️ closer |
| 13 | Human override rate and human response time (Agentic MGF p30) | ❌ invents two | ✅ |
| 14 | Read: none; Edit: per-session approval; Bash: permanent per project (p31) | ⚠️ | ⚠️ |
| 15 | AES with a key length of at least 256 bits (ICT guide p25) | ✅ | ✅ |

**gpt-4o: 3 correct, 3 partial, 1 wrong. gpt-4o-mini: 2 correct, 2 partial, 3 wrong.**

## Two-paragraph eyeball reflection

### Paragraph 1 — where the gap mattered

On the lab's ten general questions the two models were close: gpt-4o wrote about 40% more words, but rarely said anything mini got wrong. The clearest exception was L6 (production timeouts). gpt-4o suggested 30–60 s per request, in line with the deck's 30 s per-call timeout, while gpt-4o-mini suggested 1–5 s, which would have cut off almost every real answer measured this week (15–30 s). On the capstone questions the gap was more visible: gpt-4o named the Agentic framework's two oversight indicators (override rate, review time) where mini invented two, and got two of the four Research Exception conditions where mini got about one. But neither model could list the GenAI framework's nine dimensions, and both missed specifics that only the documents contain.

### Paragraph 2 — your rough rule for when to reach for the bigger model

Default to gpt-4o-mini: at about $0.0001 per answer it is 18–20× cheaper, and both models sit far below the $0.01-per-answer budget. Reach for gpt-4o only for synthesis questions where a near-miss is costly, and not as a substitute for retrieval: on regulator-specific facts the bigger model was still wrong or vague on 4 of 7 questions. The answer to "why not use the more capable model for everything?" is that the gap that matters for this capstone is grounding, not model size; retrieval over the IMDA / PDPC / MAS corpus (W6–W11) should fix more errors than a 20× more expensive model does.

## Confidence calibration

Both models reported 0.85–0.95 confidence on almost every answer, including the clearly wrong ones (for example mini's invented nine dimensions at 0.9), so self-reported `confidence` is not usable as a correctness signal here.


