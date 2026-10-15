# W2 capstone baseline: governance questions without retrieval

**What this is:** the 20 questions in `data/capstone_questions.csv`, about Singapore AI and data governance (IMDA, PDPC, MAS), run through the Week 2 pipeline against the real OpenAI API with **no retrieval and no corpus**. `gpt-4o-mini` answers from its training data alone.

**Why:** this records a *before-RAG* baseline. Once the corpus is chunked (W7) and retrieval is added (W11), the same questions can be re-run and compared answer by answer. It is not part of the W2 lab submission; the lab run uses `data/questions.csv`.

- **Run:** `results.db` run 13, 2026-10-15, 20 questions in 19.17 s, 0 retries, `use_fake=false`
- **Full output:** [`w2-capstone-baseline.json`](w2-capstone-baseline.json) (summary + all 20 answers)
- **Re-run:**
  ```bash
  python -m src.pipeline.pipeline --questions data/capstone_questions.csv
  ```
  Note: this overwrites `results.json`. Copy it here first if you want to keep it, then `git checkout -- results.json`.
- **Query later:** `python -m src.pipeline.query_results FEAT` (or any word from a question)

## First observations

Checked only where the correct answer is well established; everything else waits for grading against the source documents once they are in the corpus.

| # | Question | Model's answer | Correct answer | Verdict |
|---|---|---|---|---|
| 14 | What are MAS's FEAT principles, and what does each letter stand for? | **F**easibility, **E**quity, **A**ccountability, **T**ransparency | **F**airness, **E**thics, **A**ccountability, **T**ransparency (MAS, 2018) | ❌ Hallucinated: two of the four letters are wrong |
| 6 | What does the Model AI Governance Framework for Generative AI (2024) cover, and how many dimensions? | "four key dimensions" (governance structures, risk management, operationalisation, …) | **Nine** dimensions (IMDA / AI Verify Foundation, May 2024) | ❌ Wrong count and invented dimension names |

This is the second time the FEAT question has gone wrong without grounding. In Week 1 (`docs/runs/02-mas-feat-principles.txt`) the model invented a fifth principle, "Security"; here it renamed two of the four. Different wrong answers to the same question are exactly what ADR-0001's decision boundary is for: answer only from retrieved passages, otherwise say "I don't know".

## To do in later weeks
- [ ] Grade all 20 answers against the IMDA, PDPC and MAS source documents once they are in the corpus (W7).
- [ ] Re-run these questions with retrieval (W11) and compare against this file.
- [ ] Use the right/wrong counts as the first data point for evaluation (W18).

> Drafted by Claude Code. The two verdicts above come from widely published facts. Confirm them against the source documents when you build the corpus, and don't treat the other 18 answers as correct until they are graded.
