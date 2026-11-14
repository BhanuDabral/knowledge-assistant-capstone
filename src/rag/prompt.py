"""src/rag/prompt.py — the grounded-prompt pieces of naive RAG (W6).

No imports from the rest of the project, so src/pipeline/llm.py can use it
without a circular import (src/rag/naive_rag.py imports llm).
"""
from __future__ import annotations

RAG_INSTRUCTIONS = (
    "Answer using ONLY the context passages below, taken from the IMDA, PDPC and MAS "
    "documents. Put the ids of the passages you used (the text in square brackets) in "
    "`sources`. If the passages do not contain the answer, say that you don't know and "
    "name the publication to check; do not answer from memory."
)


def format_context(hits: list[dict]) -> str:
    """Each passage headed by its id, document and pages, so the model can cite it."""
    return "\n\n".join(
        f"[{h['chunk_id']}] ({h['source']}, p.{h['page_start']}"
        + (f"-{h['page_end']}" if h["page_end"] != h["page_start"] else "") + f")\n{h['text']}"
        for h in hits
    )


def rag_prompt(question: str, context: str) -> str:
    """The user turn the model sees: instructions, passages, then the question."""
    return f"{RAG_INSTRUCTIONS}\n\nCONTEXT:\n{context}\n\nQUESTION: {question}"
