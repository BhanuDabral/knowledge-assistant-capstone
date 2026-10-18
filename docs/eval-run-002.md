# Eval run 002 — rubric v2 + corrected ideal answers

**Date:** 18/10/2026 · **Labels:** `eval-run-001-rubric-v2` (re-judge) and `eval-run-002` (fresh run)
**Candidate:** `/ask_batched`, gpt-4o-mini, no retrieval, **no system prompt** (same as eval-run-001)
**Judge:** gpt-4o, temperature 0, **rubric v2** (`RUBRIC_VERSION = "v2"` in `src/eval/judge.py`)

> **Drafted by Claude Code — review and reword.**

## What changed since eval-run-001

1. **Rubric v2:** three sharpenings agreed after the blind calibration (`docs/judge-calibration.md`):
   format scores usability only; generic filler is harmless context, named inventions are not;
   accuracy 1 means none of the ideal's facts is present.
2. **Ideal answers:** 9 of 20 reworded for precision (`docs/golden-set-notes.md`, review log). No facts changed.

To separate the two, the eval-run-001 answers were **re-judged** with rubric v2
(`python scripts/run_eval.py --rejudge eval-run-001 --label eval-run-001-rubric-v2`), then a fresh run was made.

## Results

| Run | What differs from the row above | accuracy | groundedness | format | acc 4/3/2/1 |
|---|---|---|---|---|---|
| eval-run-001 | — | 1.65 | 1.70 | 3.40 | 2/1/5/12 |
| eval-run-001-rubric-v2 | rubric only (identical answers, old ideal wording) | 1.45 | 1.65 | 3.50 | 0/2/5/13 |
| eval-run-002 | new answers + corrected ideal answers | 1.40 | 1.50 | 3.45 | 1/1/3/15 |

Cost: re-judge $0.073; eval-run-002 $0.075 (candidate $0.0019 + judge $0.0734).

## Calibration against rubric v2 (your same blind scores, same answers)

| | rubric v1 | rubric v2 |
|---|---|---|
| Exact agreement | 15/30 (50%) | **17/30 (57%)** |
| Within-1 | 29/30 (97%) | **30/30 (100%)** |
| Disagreements > 1 | 1 (g019 format) | **0** |

## What this tells you

- **Most of the drop is the rubric, not the app.** On identical answers, v2 is stricter on
  accuracy (−0.20) because "1 = none of the ideal's facts" now applies to answers that only
  sounded partly right. It is slightly kinder on format (+0.10) because content no longer leaks into it.
- **The format fix worked:** g019 (a confident wrong fine) went from format 1 to 4; it is still 1/1 on
  accuracy and groundedness, where it belongs.
- **Single runs are noisy per question.** Fresh answers changed a lot between runs: g008 went from a vague
  answer to a charity-sector hallucination ("Fundraising Transparency…", 1/1/1); g001 swapped Ethics for an
  invented "Robustness and Safety" (accuracy 3 → 2). Compare **averages over the 20**, and treat a ±0.2
  change as noise unless it repeats.
- **Still lenient:** g020 scored 4/4/4 for declining because of a training cut-off rather than the documents'
  scope. Watch for this in spot-checks.
- **The judge only partly follows the groundedness clarification:** on g018 it still penalised "organizational
  policies" filler, the rubric's own example of harmless context. Don't sharpen further on 10 entries
  (risk of over-fitting the rubric); re-check when the golden set grows to 50.

## Baseline going forward

**eval-run-002 (accuracy 1.40, rubric v2) is the comparison point for W6 retrieval.** eval-run-001 (1.65)
stays in the ADR as the M1 number measured with rubric v1. The two are not directly comparable.
