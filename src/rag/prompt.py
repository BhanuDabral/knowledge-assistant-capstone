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


# W7: a streamed answer has no `sources` field (W6 measured: only 10/20 stream answers named a
# passage), so the streaming path asks for the ids inline instead. The tool-call path is unchanged.
RAG_INSTRUCTIONS_INLINE = (
    "Answer using ONLY the context passages below, taken from the IMDA, PDPC and MAS "
    "documents. After each fact, cite the id of the passage it comes from in square "
    "brackets, exactly as written above the passage, e.g. [feat-principles-final:p5:c12]. "
    "If the passages do not contain the answer, say that you don't know and name the "
    "publication to check; do not answer from memory."
)


def format_context(hits: list[dict]) -> str:
    """Each passage headed by its id, document and pages, so the model can cite it."""
    return "\n\n".join(
        f"[{h['chunk_id']}] ({h['source']}, p.{h['page_start']}"
        + (f"-{h['page_end']}" if h["page_end"] != h["page_start"] else "") + f")\n{h['text']}"
        for h in hits
    )


def rag_prompt(question: str, context: str, inline_citations: bool = False) -> str:
    """The user turn the model sees: instructions, passages, then the question.

    inline_citations (W7): for the streamed /ask answer, which has no `sources` field.
    """
    instructions = RAG_INSTRUCTIONS_INLINE if inline_citations else RAG_INSTRUCTIONS
    return f"{instructions}\n\nCONTEXT:\n{context}\n\nQUESTION: {question}"
