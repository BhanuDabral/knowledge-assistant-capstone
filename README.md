# Capstone — Knowledge Assistant

A 30-week build of a Q&A assistant over a small document corpus, completed as part of
the *Agentic AI & RAG Engineering* programme.

## Corpus

Thematic Summary of Singapore AI & Data Governance Frameworks. Source: IMDA, MAS

## Structure

- `src/` — application code
  - `src/hello_llm.py` — Week 1 single LLM call
  - `src/pipeline/` — Week 2 async batch pipeline (settings, logging, pipeline, store, query)
- `data/questions.csv` — the 20 Week 2 lab questions (the course's lab-package set)
- `data/capstone_questions.csv` — the 20 capstone questions, each with its proposed source document (and page where confirmed)
- `data/corpus/SOURCES.md` — the 15-document IMDA / PDPC / MAS corpus with official URLs (PDFs kept locally in the gitignored `data/corpus/raw/`)
- `logs/pipeline.log` — JSON log, one record per event
- `results.json` / `results.db` — latest run artefact / every run in SQLite
- `docs/adr/` — Architecture Decision Records (one per major design choice)
- `docs/runs/` — saved LLM outputs for evidence and reference

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your OPENAI_API_KEY
```

Run everything from the repo root so `load_dotenv()` picks up `.env`.

## Week 1

- [x] Set up repo + secrets discipline
- [x] Build `hello_llm.py` (Lab Step 2)
- [x] Write ADR v1 (Lab Step 3)
- [x] System-prompt voice activity (`docs/runs/week1-activity.md`)

## Week 2 — Async batch pipeline

Run from the repo root (with `.venv` active):

```bash
python -m src.pipeline.pipeline              # all 20 questions (real API by default)
python -m src.pipeline.pipeline --limit 3    # only the first 3 questions
python -m src.pipeline.pipeline --questions data/capstone_questions.csv   # another question CSV
python -m src.pipeline.query_results --runs  # list saved runs
python -m src.pipeline.query_results RAG     # search saved answers
```

- [x] `src/pipeline/` package with typed `Settings` + JSON logger (Lab Step 1)
- [x] `pipeline.py` built from the starter: `ask_llm`, retry with backoff, `gather`, JSON logs (Lab Step 2)
- [x] CSV input, batches of 5, `RunSummary`, `results.json`, real OpenAI API (Lab Step 3)
- [x] SQLite persistence (`runs` + `answers`) and query script (Lab Step 4)
- [x] `--limit N` flag built with a coding assistant, verification in `docs/lab2-assistant-notes.md` (Lab Step 5)
- [x] `as_completed` vs `gather` activity (`docs/runs/week2-activity.md`)
- [x] Capstone baseline: the 20 capstone questions answered **without retrieval**, the "before RAG" reference; 7 graded against source pages, 2 correct / 3 partial / 2 wrong (`docs/runs/w2-capstone-baseline.md`)

**How Week 2 relates to the capstone:** the pipeline is the engine, not yet the knowledge assistant. It asks the LLM directly; the IMDA/MAS corpus is chunked in W7 and retrieved from in W11, and the baseline above is what those weeks get compared against.

## Week 3 — API, UI and tests

Run from the repo root with `.venv` active (two terminals):

```bash
uvicorn api.main:app --port 8000                                   # terminal 1: the API (docs at http://localhost:8000/docs)
streamlit run ui/app.py --server.port 8501 --server.address localhost   # terminal 2: the UI at http://localhost:8501
pytest                                                             # 4 mocked tests, no API calls
python scripts/stress_test.py --requests 10 --concurrent 3         # quick stress replay (real API calls)
```

- [x] `api/main.py`: `/ask` (streaming), `/ask_batched`, `/health`, plus `/metrics` (W3 activity)
- [x] `ui/app.py`: Streamlit UI streaming from `/ask`
- [x] `tests/`: 4 mocked unit tests (`PIPELINE_USE_FAKE=1` set in `tests/conftest.py`)
- [x] `docs/wk3-stress-notes.md`: 4 stress findings plus known limits
- [x] `docs/adr/0002-api-contract.md`: v1 contract locked (3 open items for review)
- [x] `docs/runs/week3-activity.md`: `/metrics` activity

`PIPELINE_USE_FAKE=1` switches the pipeline to the fake LLM (no API cost); unset, it uses the real OpenAI API.

## Week 4 — LLM foundations + model landscape

Same `/ask`, `/ask_batched`, `/health` contract; richer insides.

```bash
python scripts/migrate_store.py data/answers.db                    # create / upgrade the W4 answers table (safe to rerun)
python scripts/compare_models.py                                   # 10 lab questions: gpt-4o-mini vs gpt-4o (real API)
python scripts/compare_models.py --questions data/capstone_questions.csv --db data/answers_capstone.db
python scripts/compare_models.py --models llama3.2:3b              # local model (needs `ollama serve` running)
pytest                                                             # 33 tests, offline
```

- [x] Step 1: tool-calling `ask_llm` (`src/pipeline/llm.py`) → `Answer` + `confidence`, `sources`, `schema_version="v1"` (`src/pipeline/models.py`)
- [x] Step 2: real LLM streaming on `/ask`; real `cost_usd` from `response.usage` (`src/pipeline/cost.py`); answers saved to `data/answers.db` (`src/pipeline/answer_store.py`); tiktoken guard (over 2,000 tokens → 422)
- [x] Step 3: gpt-4o-mini vs gpt-4o: 20.4× cost gap on the lab set (`docs/lab4-model-comparison.md`)
- [x] Step 4: ADR 0002 extended: schema versioning rule, ≤ $0.01/answer budget, gpt-4o-mini as default
- [x] Activity: Ollama `llama3.2:3b` as a third, $0 model (`docs/lab4-ollama-activity.md`)

Course-reference fixes made here: Settings gained `openai_api_key` (masked), `max_retries`, `retry_delay_s` (the reference real-API path crashed without them); the comparison script reads `question`/`text` columns and labels fake runs; two comma rows in the lab CSV are quoted.


## Week 5 — Prompting + eval literacy + M1 (DR #1)

Contract unchanged; new: a golden set, an LLM judge, pairwise and Critic-Creator, and the M1 documents.

```bash
python -c "from src.eval.golden import validate_golden_set; print(validate_golden_set('data/golden_set.jsonl')['coverage'])"
uvicorn api.main:app --port 8000                                   # terminal 1 (run_eval calls /ask_batched)
python scripts/run_eval.py --label eval-run-002                    # terminal 2: judge gpt-4o over 20 entries (~$0.07)
python scripts/run_pairwise.py                                     # prompt v1 vs v2, both orders (~$0.09)
python scripts/run_critic_creator.py --golden-id g015              # Critic-Creator trace (~$0.02)
python scripts/compute_calibration.py --calibration-file docs/judge-calibration.md --db data/answers.db --label eval-run-001
PIPELINE_SYSTEM_PROMPT_FILE=data/prompt-v2.txt uvicorn api.main:app --port 8000   # serve with the v2 system prompt
pytest                                                             # 77 tests, offline
```

- [x] Step 0: `eval_runs` table in `data/answers.db` (`src/pipeline/answer_store.py`)
- [x] Step 1: Stakeholder Map (`docs/adr/0001-stakeholder-map.md`, draft with [YOU] markers)
- [x] Step 2: 20-entry golden set, 14 / 4 / 2, ideal answers cited to source pages (`data/golden_set.jsonl`, `docs/golden-set-notes.md`)
- [x] Step 3: judge (`src/eval/judge.py`) → eval-run-001: accuracy 1.65, groundedness 1.70, format 3.40 — no retrieval yet (`docs/eval-run-001.md`)
- [x] Step 4: pairwise v1 vs v2 (one refusal rule): v2 8, v1 1, tie 4, ambiguous 7 (`docs/prompt-pairwise-001.md`)
- [x] Step 5: Critic-Creator on g015: flat 2.33 over 3 rounds (`docs/critic-creator-trace.md`)
- [x] Step 6: ADR 0001 v1 (Locked) + DR #1 1-pager (`docs/dr/`)
- [x] Take-home A: blind calibration — exact 50% → 57%, within-1 97% → 100% after rubric v2 (`docs/judge-calibration.md`)
- [x] eval-run-002 with rubric v2 + corrected ideal answers: accuracy 1.40 — no-prompt reference (`docs/eval-run-002.md`; re-judge with `--rejudge`)
- [x] Prompt v2 shipped (`PIPELINE_SYSTEM_PROMPT_FILE` in `.env`); eval-run-003: accuracy 1.65, groundedness 1.95 — **the W6 comparison point** (`docs/eval-run-003.md`)
- [ ] DR #1 feedback (pending): ADR open question 3 and section 10

The W5 code bundle was not available, so `src/eval/*` and the three run scripts were written from the lab guide's spec. The course's `compute_calibration.py` was fixed (it compared the judge with itself).
