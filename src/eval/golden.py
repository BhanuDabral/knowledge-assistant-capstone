"""src/eval/golden.py — load and validate the golden set (W5 Lab Step 2).

Written by Claude Code from the W5 lab guide's spec and `golden_set_demo.ipynb`
(the course bundle's `AI-RAG_W5_golden_reference.py` was not available).

The golden set is JSONL: one entry per line,
    {"id": "g001", "question": "...", "ideal_answer": "...", "notes": "happy-path. ...", "source": "..."}

`notes` must start with the bucket — `happy-path`, `harder` or `edge` — because
validate_golden_set() reads the first word to compute coverage (target 14/4/2).
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, Field

BUCKETS = ("happy", "harder", "edge")


class GoldenEntry(BaseModel):
    """One golden question with the facts a good answer must contain."""
    id: str = Field(pattern=r"^g\d{3}$")                    # g001 … g999, stable and git-friendly
    question: str = Field(min_length=1)                     # as a real user would phrase it
    ideal_answer: str = Field(min_length=1)                 # the facts, not one fixed phrasing
    notes: str = Field(min_length=1)                        # bucket first, then why it is interesting
    source: str = ""                                        # document + page(s) the answer comes from

    @property
    def bucket(self) -> str:
        return bucket_of(self.notes)


def bucket_of(notes: str) -> str:
    """'happy-path. …' -> 'happy'; 'harder · multi-hop. …' -> 'harder'; 'edge. …' -> 'edge'."""
    first = re.split(r"[\s.·,:;-]+", notes.strip().lower(), maxsplit=1)[0]
    if first not in BUCKETS:
        raise ValueError(f"notes must start with happy-path / harder / edge, got {notes[:30]!r}")
    return first


def load_golden(path: str | Path) -> list[GoldenEntry]:
    """Parse and validate every non-blank line. Fails loudly on the first bad line."""
    entries = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = GoldenEntry(**json.loads(line))
            entry.bucket                                    # validates the notes prefix
        except Exception as exc:
            raise ValueError(f"{path}:{n}: {exc}") from exc
        entries.append(entry)
    return entries


def validate_golden_set(path: str | Path) -> dict:
    """Load the set, reject duplicate ids, and report coverage per bucket."""
    entries = load_golden(path)
    ids = [e.id for e in entries]
    dupes = sorted(i for i, c in Counter(ids).items() if c > 1)
    if dupes:
        raise ValueError(f"duplicate ids: {dupes}")
    counts = Counter(e.bucket for e in entries)
    return {
        "path": str(path),
        "n": len(entries),
        "ids": ids,
        "coverage": {b: counts[b] for b in BUCKETS if counts[b]},
    }


def get_entry(path: str | Path, golden_id: str) -> GoldenEntry:
    """One entry by id (used by the Critic-Creator script)."""
    for e in load_golden(path):
        if e.id == golden_id:
            return e
    raise KeyError(f"{golden_id} not in {path}")
