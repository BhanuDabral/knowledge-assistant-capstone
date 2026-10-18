# Eval run 001 — M1 evaluation baseline

**Date:** 18/10/2026 · **Label:** `eval-run-001` · **Golden set:** `data/golden_set.jsonl` (20 entries, 14/4/2)
**Candidate:** the app's `/ask_batched` as of W4 — `gpt-4o-mini`, tool-calling, **no retrieval, no system prompt**
**Judge:** `gpt-4o`, temperature 0, rubric in `src/eval/judge.py` (accuracy / groundedness / format, 1–4)

> **Drafted by Claude Code — review and reword.** Numbers are from the run
> (`scripts/run_eval.py`, rows in `data/answers.db` → `eval_runs`). The
> spot-check notes are Claude Code's reading of the verdicts; your own blind
> calibration is the take-home (`docs/judge-calibration.md`).

## Aggregate stats

```
n entries scored   : 20
avg accuracy       : 1.65
avg groundedness   : 1.70
avg format         : 3.40
accuracy 4 / 3 / 2 / 1 : 2 / 1 / 5 / 12
cost (candidate + judge) : $0.001982 + $0.067212
wall-clock         : 70.3s
```

| Bucket | n | accuracy | groundedness | format |
|---|---|---|---|---|
| happy-path | 14 | 1.57 | 1.64 | 3.57 |
| harder | 4 | 1.50 | 1.50 | 3.25 |
| edge | 2 | 2.50 | 2.50 | 2.50 |

**Read this against the guide's "typical 3.0–3.6".** The guide's warning
(< 2.5 means a broken `/ask_batched` or bad ideal answers) was checked: the API
returned well-formed answers for all 20, and every ideal answer cites its source
page. The score is low because this capstone's questions are **document-specific**
(named lists, conditions and definitions from 2024–2026 regulator publications)
and the app has **no retrieval yet** — the model answers from memory and fills
gaps by inventing plausible lists. That is the problem ADR 0001 sets out to solve.

## Per-entry breakdown

```bash
sqlite3 -header -column data/answers.db "SELECT golden_id, accuracy a, groundedness g, format f FROM eval_runs WHERE eval_run_label='eval-run-001' ORDER BY golden_id"
```

| id | a/g/f | What happened |
|---|---|---|
| g001 | 3/3/4 | All four FEAT principles right; docked for added descriptions |
| g002 | 1/1/3 | Listed GDPR-style bases (contract, legal obligation) instead of Business Improvement / Research |
| g003 | 2/2/4 | Got "public benefit"; invented "data must be anonymised" (the source says the opposite) |
| g004 | 1/1/4 | Listed Transparency / Accountability / Fairness / Safety instead of the four dimensions |
| g005 | 1/1/4 | Expanded SAFR as "System for Automated Financial Risk" |
| g006 | 1/1/4 | Nine invented dimensions, no overlap |
| g007 | 1/1/4 | Generic ML lifecycle, not MindForge's five stages |
| g008 | 2/2/3 | Vague purpose; also expanded FEAT as "Fairness, **Equity**, …" |
| g009 | 1/1/3 | Invented offences ("failure to take security measures") |
| g010 | 1/2/3 | Generic processor duties; missed data mapping + provenance record |
| g011 | 1/1/4 | Invented "Review Engagement Rate", "Decision Reversal Rate" |
| g012 | 4/4/3 | AES-256 — correct |
| g013 | 2/2/3 | Generic proactive/reactive; missed FEAT P12 vs P13–14 link |
| g014 | 1/1/4 | Invented roles (AI Ethics Officer, Data Steward, …) |
| g015 | 1/1/3 | "Alignment with user values" — missed "never more than the user's own permissions" |
| g016 | 2/2/4 | Model right; system/use case vague; missed why use case is the governance unit |
| g017 | 1/1/3 | Accepted the false premise ("three elements") and invented them |
| g018 | 2/2/3 | Read/Edit right in spirit; missed Bash "permanent per project" and the case-study source |
| g019 | 1/1/1 | Quoted a fine figure from memory (€30m / 6%, an early-draft figure; Art. 99 of the adopted Act says €35m / 7% — Claude Code's knowledge, not the corpus); should have declined |
| g020 | 4/4/4 | Declined — but because "2026 is in the future" (training cut-off), not because the documents don't cover it |

## Three things found

**Where it's strong.** Format (3.40): answers are short, direct and readable.
And general security knowledge (g012, AES-256) — the one question whose answer
is industry-standard rather than document-specific.

**Where it's weak.** Every question whose answer is a **named list or definition
from a specific document** (g004–g007, g009, g011, g014): the model invents a
plausible list instead of saying it doesn't know. Confidence stayed at 0.85–0.95
throughout (W4 finding), so the app gives users no warning. The edge case g019
confirms the ADR's worry: asked something out of scope, it answers confidently
— with an outdated figure.

**Where the judge looked wrong (spot-check of all 20, not just 5).**
- *Lenient:* **g020** scored 4/4/4 for a refusal given for the wrong reason;
  **g012** scored accuracy 4 although its own reasoning names a missing fact
  (rubric says that's a 3).
- *Missed an error:* **g008** — the judge did not flag "FEAT = Fairness,
  Equity, …", exactly the "subtle substitution" the rubric's level-4 anchor names.
- *Rubric ambiguity:* **g019** got format 1 for wrong *content*; format should
  judge usability only. **g001** lost accuracy for extra descriptions that are
  correct.
- 5 questionable verdicts out of 20 (25%) — mostly ±1, none that would change
  the headline. Worth one rubric sharpening (below) and your blind calibration.

## What I'll change before DR #1 (max 3)

1. **Sharpen the rubric:** format scores usability only (never content); a
   decline must cite the documents' scope, not a training cut-off, to score 4.
2. **Ship a system prompt** that tells the model to say "I don't know" for
   questions outside its documents — tested in `docs/prompt-pairwise-001.md`.
3. **Do the blind calibration** (`docs/judge-calibration.md`) before trusting
   the judge for W6+ retrieval runs.

**The real fix is W6–W8 retrieval:** this baseline is the "before" number
every retrieval change will be measured against.
