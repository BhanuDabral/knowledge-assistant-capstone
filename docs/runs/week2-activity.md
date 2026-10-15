# Week 2 Activity — `as_completed` vs `gather`

**Function added:** `run_batch_stream` in `src/pipeline/pipeline.py`
**LLM:** `fake_ask_llm` (random 0.3–1.5 s latency per call, no API cost)
**Questions (input order):**

1. What is RAG in one sentence?
2. Name three uses of vector databases.
3. Why might an LLM hallucinate?
4. Explain async and await in plain language.
5. What is the difference between a chatbot and an agent?

## Clean run (`fail_rate=0.0`)

```
run_batch_stream — fail_rate=0.0
  ✓ An agent is a loop that uses an LLM to decide what to do nex...      ← Q5 finished first
  ✓ Vector databases power semantic search, RAG context retrieva...      ← Q2
  ✓ LLMs hallucinate when they produce confident text that isn't...      ← Q3
  ✓ RAG combines retrieval over a document corpus with an LLM, s...      ← Q1
  ✓ Async Python lets one program work on many I/O-bound tasks a...      ← Q4

returned 5 answers in 1.44s
```

Answers arrived in the order 5, 2, 3, 1, 4, not the input order 1–5. The whole run took about as long as the slowest single call.

## With failures (`fail_rate=0.4`)

```
run_batch_stream — fail_rate=0.4
  ✓ Async Python lets one program work on many I/O-bound tasks a...      ← Q4, no retry
  ✓ RAG combines retrieval over a document corpus with an LLM, s...      ← Q1, no retry
  ✓ Vector databases power semantic search, RAG context retrieva...      ← Q2, 1 retry (1 s backoff)
  ✓ An agent is a loop that uses an LLM to decide what to do nex...      ← Q5, 2 retries (1 s + 2 s)
  ✓ LLMs hallucinate when they produce confident text that isn't...      ← Q3, 2 retries (1 s + 2 s)

returned 5 answers in 6.53s
```

The retry warnings in the log match the order: the two questions with no failures arrived first, the one with a single retry came next, and the two that retried twice arrived last, about 5 seconds after the first answers. The run took 6.53 s against 1.44 s for the clean run.

## What I observed

- `as_completed` made the **finish order visible**: each answer printed the moment its call completed, so the questions slowed down by retry backoff visibly arrived last. `gather` hides this, because it returns all results together, in input order, only once the slowest call is done.
- I'd use **`gather`** when the next step needs every result, and in input order, before it can start, as in the W2 lab where `RunSummary` adds up all 20 answers. I'd use **`as_completed`** when results can be used one at a time as they arrive, such as streaming answers to a UI or stopping at the first acceptable answer.

> Note: these observations were drafted by Claude Code from the actual run output above. Review and reword them in your own words before submitting.
