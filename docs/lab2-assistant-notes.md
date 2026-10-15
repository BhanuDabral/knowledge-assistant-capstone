# Lab 2 — Coding-assistant verification note

## The change
Added a `--limit N` command-line flag to `src/pipeline/pipeline.py` that processes only the first N questions from `data/questions.csv`. Why: real-API runs of all 20 questions take ~30 s and cost money on every run, and the lab's Step 3f trial run otherwise needs a hand-edited CSV and a temporary change to `Settings.questions_csv`. Only the `__main__` block of `pipeline.py` changed.

## The ask
Assistant: **Claude Code** (Claude Opus 5.5), in VS Code.

> Add a `--limit N` flag to `python -m src.pipeline.pipeline` that runs only the first N questions from the CSV. Keep the change inside `__main__`; use the standard library only (no new dependency); reject N < 1 with a clear error; log how many questions are actually run; leave `ask_llm`, retry, batching, `RunSummary` and persistence unchanged.

## What it produced
A 17-line addition to `__main__` only (`git diff` showed no other changes):
- `argparse` (standard library) with one option, `--limit N` (`type=int`, default `None`, help text).
- `parser.error("--limit must be 1 or more")` when N < 1. A non-integer is rejected by `argparse` itself.
- After `load_questions(...)`: `questions = questions[: args.limit]` plus a log line `--limit N: running the first M questions`.

## What I verified before accepting
- **Diff read:** `git diff src/pipeline/pipeline.py` showed changes only inside `if __name__ == "__main__":`. `load_questions`, `ask_llm`, `ask_llm_with_retry`, `run_in_batches`, `summarise_run` and `store.py` were untouched, so the persisted `RunSummary` simply reports the smaller `n_questions`.
- **Test run, before the change:** `python -m src.pipeline.pipeline --limit 3` silently ignored the flag and ran all 20 (`wrote 20 answers … in 26.63s`).
- **Test runs, after the change:**

  | Command | Result |
  |---|---|
  | `--help` | Shows `--limit N   process only the first N questions from the CSV (N >= 1)` |
  | `--limit 0` | `error: --limit must be 1 or more` (exit code 2) |
  | `--limit abc` | `error: argument --limit: invalid int value: 'abc'` (exit code 2) |
  | `--limit 3` (real API) | `wrote 3 answers … in 4.72s`; log: `--limit 3: running the first 3 questions` |
  | `--limit 50` (real API) | `wrote 20 answers` (slicing past the end is safe) |
  | `--limit 5` (fake LLM, `use_fake` temporarily `True`) | `wrote 5 answers … in 1.27s`, so both the fake and real paths work |
  | no flag (real API, regression) | `wrote 20 answers … in 31.11s`, so the default behaviour is unchanged |

  `python -m src.pipeline.query_results --runs` shows each of these runs with the matching `questions` count (3, 20, 5, 20).
- **Security check:**
  - No new dependencies: `git diff requirements.txt` is empty, and `argparse` is in the standard library.
  - Secrets are handled exactly as before: still `load_dotenv()` and `OPENAI_API_KEY` from `.env`, which is gitignored and not tracked.
  - The only new input is `--limit`, which is parsed as an `int` and checked to be ≥ 1. It is used only to slice a Python list and never reaches SQL or a shell, so there is no injection path.

## What I changed before committing
Nothing in the code. `settings.py` was temporarily flipped to `use_fake=True` for the fake-path test, then restored with `git checkout -- src/pipeline/settings.py`, so the committed defaults remain `use_fake=False`, `fail_rate=0.0`.

> Note: drafted by Claude Code from the actual commands and outputs of this session. Review it and add your own observations before submitting.
