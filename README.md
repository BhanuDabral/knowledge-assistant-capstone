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
