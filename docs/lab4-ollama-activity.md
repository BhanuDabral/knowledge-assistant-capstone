# W4 Activity — Ollama as the third model

## Setup (2026-10-17, M1 MacBook, 16 GB RAM)

- **Ollama 0.40.5**, official macOS app from ollama.com (GitHub release). Code signature and Apple notarization verified before install. `brew install ollama` failed first on a pre-existing Homebrew `ca-certificates` link conflict and was not forced.
- Server started with `ollama serve` (no login item). `llama3.2:3b` pulled (2.0 GB).
- `cost.py` already had `"llama3.2:3b": (0.0, 0.0)`.
- `src/pipeline/llm.py`: models listed in `LOCAL_MODELS` route to `http://localhost:11434/v1`. `tool_choice` is omitted for Ollama, which doesn't support it. If the local model skips the tool call, it falls back to schema-constrained JSON (`response_format=json_schema`) and logs why.
- Same 10 lab questions via `python scripts/compare_models.py --models llama3.2:3b`.

## Three-way comparison (`data/answers.db`, course script `compare_three_models.py`)

```
model         n    total_$     avg_$       avg_conf
gpt-4o        10   0.014793    0.001479    0.92
gpt-4o-mini   10   0.000724    0.000072    0.90
llama3.2:3b   10   0.000000    0.000000    0.75
```

Time for the 10 questions: about 14 s (gpt-4o-mini), 15 s (gpt-4o), **103 s** (llama3.2:3b, including 7 retries).

## What happened

- **Tool-call compliance was shaky, and validation caught it.** On 7 of 10 questions llama3.2:3b's first answer was rejected by the `Answer` model: `sources` came back as a JSON *string* (`'["Wikipedia"]'`) or as a list of objects (`{'value': 'response usage'}`). The retry loop asked again until the shape was valid. That is the cost of a small model: it was correct structurally in the end, but about 7× slower than gpt-4o-mini here.
- **Malformed values can still slip through.** One saved answer lists `"[]"` (a string) as a source.
- **Phrasing matters.** "What is RAG?" got a list of dictionary meanings of *rage* / *rag* with a made-up source ("Wikipedia", confidence 0.8). The full question ("What is Retrieval-Augmented Generation, in two sentences?") got a correct definition.
- **Confidence is lower on average (0.75)**, as the course predicts, but not reliably: it reported 1.0 on one answer.
- **All three models got the schema-versioning question (L10) wrong by the course's own rule.** They say `schema_version` should change on any structural change, including additions, which ADR 0002 says must *not* bump the version.

## Reflection

Local is genuinely free: the cost ratio to either hosted model is infinite, which makes it useful for iterating on prompts and for data that must not leave the machine. On this laptop it was also clearly worse: slower, less compliant with the structured-output contract, and wrong on short or ambiguous questions where gpt-4o-mini was fine. For this capstone the default stays gpt-4o-mini; a local model would earn its place only if a stakeholder required that governance documents never leave the device.

## Removing Ollama later (optional)

```bash
/Applications/Ollama.app/Contents/Resources/ollama rm llama3.2:3b   # frees 2 GB
rm -rf /Applications/Ollama.app ~/.ollama
```

> Drafted by Claude Code from the actual run outputs. Review and reword it in your own words before submitting.
