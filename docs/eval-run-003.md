# Eval run 003 — prompt v2 shipped (new W6 baseline)

**Date:** 18/10/2026 · **Label:** `eval-run-003`
**Candidate:** `/ask_batched`, gpt-4o-mini, no retrieval, **system prompt v2** (`PIPELINE_SYSTEM_PROMPT_FILE=data/prompt-v2.txt` in `.env`)
**Judge:** gpt-4o, temperature 0, rubric v2 · **Golden set:** 20 entries (corrected ideal answers)

> Drafted by Claude Code from the run output — review and reword.

## Why this run exists

Prompt v2 won pairwise 001 and is now shipped. eval-run-002 was measured **without** a system prompt, so
comparing W6 retrieval results against it would mix two changes (prompt + retrieval). This run measures the
app as it now runs, so W6 changes only one thing.

## Results

| Run | System prompt | Rubric | accuracy | groundedness | format | acc 4/3/2/1 |
|---|---|---|---|---|---|---|
| eval-run-002 | none | v2 | 1.40 | 1.50 | 3.45 | 1/1/3/15 |
| **eval-run-003** | **v2** | v2 | **1.65** | **1.95** | 3.40 | 1/1/8/10 |

Cost: $0.075 (candidate $0.0020 + judge $0.0734), 61 s.

## What this tells you

- **v2 makes answers more careful, not more knowledgeable:** groundedness +0.45 (fewer invented specifics),
  accuracy +0.25 (more partly right answers: 8 at level 2 vs 3). Still no retrieval, so the named lists are
  still wrong.
- **The refusal rule is not reliable yet.** g020 declined properly ("I don't know … check official PDPC
  publications", 4/4/4), but **g019 quoted an EU AI Act fine again** (€30m / 6%), although v2 declined it in
  pairwise 001. Answers are sampled, so v2 lowers the chance of a confident out-of-scope answer but does not
  remove it. KPI 2 (honest refusals) for this run: **1 / 2**.
- **The judge broke its own format rule once:** g019 got format 1 ("unusable as it provides incorrect
  information"). Rubric v2 says format ignores correctness, and the re-judge gave the same kind of answer 4.
  The rule holds most of the time, not always: keep spot-checking.

## Baseline going forward

**eval-run-003 (prompt v2, rubric v2): accuracy 1.65, groundedness 1.95, format 3.40** is the comparison
point for W6 retrieval. Single-run differences of about ±0.2 are noise (see `docs/eval-run-002.md`); run
twice before believing a small change.

Note: the 1.65 here matches eval-run-001's 1.65 by coincidence. They used different rubrics, prompts and
ideal answers, so they are not comparable.
