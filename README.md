# Capstone — Knowledge Assistant

A 30-week build of a Q&A assistant over a small document corpus, completed as part of
the *Agentic AI & RAG Engineering* programme.

## Corpus

Thematic Summary of Singapore AI & Data Governance Frameworks. Source: IMDA, MAS

## Structure

- `src/` — application code
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
