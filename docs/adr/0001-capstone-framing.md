# ADR-0001: Capstone Framing — Singapore AI & Data Governance Assistant

- **Status:** Draft v1
- **Date:** 2026-10-12
- **Author:** Bhanu Dabral

## Context

Singapore's AI and data governance guidance is spread across separate IMDA and MAS publications, so answering a simple question such as "what does the regulator expect on fairness?" means reading several long documents. This capstone builds a grounded Q&A assistant over a small set (5–20) of those public framework documents, for practitioners who need a quick, sourced answer. An ungrounded model is not good enough here: in `docs/runs/02-mas-feat-principles.txt` plain `gpt-4o-mini` listed five FEAT principles and invented "Security", when FEAT has four (Fairness, Ethics, Accountability, Transparency).

## Decision — Solution Framing Canvas

| Box | Your answer |
|-----|-------------|
| **Inputs** | A natural-language question of one or two sentences about Singapore AI or data governance, e.g. "What does MAS expect on explainability of AI models?". |
| **Outputs** | A 2–4 sentence plain-English answer plus citations naming the source framework and section it was drawn from. |
| **Tools** | `gpt-4o-mini` for generation, and a retriever over the chunked IMDA and MAS documents (vector store to be chosen in W7). |
| **Memory** | None across calls in v1; every question is answered fresh with no conversation history. |
| **Autonomy level** | Q&A app, between Chatbot and Workflow: it retrieves and answers, and takes no actions. |
| **Decision boundaries** | It may answer only when retrieval finds supporting passages in the corpus; otherwise it says it does not know and points the user to the original IMDA or MAS publication, and it never gives legal or compliance advice. |

## Consequences

- **Positive:**
  - Answers are tied to named source passages, so a reader can check them against the framework itself.
  - An honest "I don't know" replaces confident guesses like the invented fifth FEAT principle.
  - A small, public corpus keeps the build reviewable by the cohort and free of confidential data.
- **Negative / risks:**
  - The corpus goes stale when IMDA or MAS revise a framework, so documents need a recorded version and date.
  - A wrong or misattributed citation in a regulatory domain costs more trust than a missing answer.
  - No memory means follow-up questions lose the context of the previous one.
- **Things we'll re-visit:** the retrieval-confidence threshold for answering versus declining (W12), and multi-turn memory (W14).
