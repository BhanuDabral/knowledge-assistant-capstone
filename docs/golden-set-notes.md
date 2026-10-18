# Golden set notes — `data/golden_set.jsonl`

**Date:** 18/10/2026 · **Author:** Bhanu Dabral · **Entries:** 20

> The questions are Bhanu's (W2 `data/capstone_questions.csv`), unchanged except the two
> new edge entries. The ideal answers were drafted by Claude Code from the source PDFs
> and checked against the cited pages (review log at the end).

## Coverage mix

`validate_golden_set()` reports `{'happy': 14, 'harder': 4, 'edge': 2}` —
the lesson-plan ideal.

| Golden id | Bucket | Your W2 question | Source (PDF page) |
|---|---|---|---|
| g001 | happy | Q1 FEAT principles | FEAT Principles p.6 |
| g002 | happy | Q3 PDPA exceptions for AI | PDPC AI guidelines pp.5–6 |
| g003 | happy | Q4 Research Exception conditions | PDPA Key Concepts p.74 |
| g004 | happy | Q6 Agentic MGF four dimensions | MGF Agentic pp.3–4 |
| g005 | happy | Q7 role of SAFR | SAFR v1.1 p.6 |
| g006 | happy | Q8 GenAI MGF nine dimensions | MGF GenAI p.2 |
| g007 | happy | Q9 MindForge lifecycle stages | MindForge Ops PDF p.23 |
| g008 | happy | Q10 purpose of Veritas | Veritas 3A pp.4, 6–7 |
| g009 | happy | Q11 Part 9B offences | PDPA Key Concepts p.9 |
| g010 | happy | Q12 Service Provider practices | PDPC AI guidelines pp.19–20 |
| g011 | happy | Q13 human-oversight indicators | MGF Agentic p.30 |
| g012 | happy | Q15 encryption for long-term retention | ICT guide p.25 |
| g013 | happy | Q17 proactive vs reactive transparency | Veritas 3C p.11 |
| g014 | happy | Q20 MindForge roles | MindForge Ops PDF p.115 |
| g015 | harder | Q19 delegating authority to an agent | MGF Agentic p.24 + SAFR v1.1 p.12 |
| g016 | harder | Q16 model vs system vs use case | MindForge Ops PDF pp.22–23 |
| g017 | harder | Q18 notification elements | PDPC AI guidelines pp.13–14 |
| g018 | harder | Q14 Read / Edit / Bash approvals | MGF Agentic pp.30–31 |
| g019 | edge | *new* — EU AI Act fines | not in corpus |
| g020 | edge | *new* — PDPC fines in 2026 | not in corpus |

**Why these four are "harder":** g015 needs two documents (the MGF and SAFR);
g016 needs three definitions plus *why* the handbook governs at use-case level;
g017 has a **false premise** — it asks for three elements but the guideline lists
four, so a good answer corrects the user; g018 is conditional (a different rule
per action type) and comes from a vendor **case study** inside the framework, not
the framework's own recommendation, which a careful answer should say.

**Why these two edges:** g019 is the wrong jurisdiction but *mentioned* in the
corpus (the EU AI Act appears as a reference point), which tempts a model to
fill in a fine from memory. g020 sounds like a PDPC question the corpus should
cover, but the corpus holds guidelines, not enforcement decisions. The correct
behaviour for both is the ADR 0001 decision boundary: say so and point to the
right publication.

**Dropped (kept for the 50-entry stretch):** your Q2 (the two areas of FEAT
Fairness — close to g001 and covered in the same document) and Q5 (what
distinguishes agentic from generative AI — same document as g004, and the
answer is a description rather than checkable facts). Both are good entries for
`g021+` if you grow the set.

## Sourcing

Honest ranking against the deck's scale (real users > domain expert > you at
the keyboard): these 18 questions were written by me in W2 while reading the
documents, so they sit at **"me at the keyboard, reading the source"** — better than invented, weaker than real user
questions. The two edge questions were written by Claude Code. The ideal
answers were drafted by Claude Code from the cited pages. A stronger set would
add questions from a real compliance analyst (my primary user in the
Stakeholder Map).

## Hardest to write

The edge cases were hardest. Proving a question is *not* answered by the corpus
meant checking all 15 documents, and the EU AI Act turned out to be mentioned in two
of them, just never its penalties. The harder bucket taught a different lesson: g017
showed that one of my own questions carried a wrong premise (three elements where the
guideline lists four), which is itself worth testing.

## Ideal-answer review checklist (do this before DR #1)

For each entry, open the PDF at the cited page and tick when the ideal answer
says nothing the page doesn't:

- [x] g001 – g005
- [x] g006 – g010
- [x] g011 – g014
- [x] g015 – g018 (harder: check every clause)
- [x] g019 – g020 (edge: confirm the corpus really doesn't answer them)

### Review log — 18/10/2026 (by Claude Code, clause by clause against the verbatim source text)

> Claude Code drafted these answers and then reviewed them, so this is a self-check.
> A spot-check of a few entries by you is still worth doing (suggested: g008, g012, g018).

No ideal answer stated a wrong fact. 9 of 20 were made more precise, mostly about
**who says what**. That matters because the judge scores groundedness against
these answers.

| Entry | What changed | Why (source) |
|---|---|---|
| g001 | Source now also cites p.5 | "can guide all firms using AIDA" is in §3.1, p.5, not p.6 |
| g005 | Says SAFR *defines data structures, evaluation logic and escalation contracts*; "the paper says" (not "MAS states") it is not guidance | Wording of SAFR v1.1 p.6 |
| g008 | "MAS-led industry consortium" → "an MAS initiative carried out with the Veritas Consortium" | The document says "MAS Veritas Phase 2 project" and "Veritas Consortium"; it never says "MAS-led consortium" |
| g010 | Separated the two ideas | §11.3: the records help detect unauthorised changes and judge if a breach is notifiable; §11.4 (separately): support customers' obligations |
| g012 | AES-256 is the guide's **example** for long-term retention, inside its advice to review the method periodically | p.25 says "e.g. AES … minimum of 256-bits key length"; it is not a standalone mandate |
| g015 | Added "as a rule of thumb" and "generally" | MGF p.24 uses exactly these qualifiers |
| g016 | Added "while letting each institution choose its own unit" | MindForge p.23: "FIs may each choose the basic unit … in their own context" |
| g018 | The adjustable per-project defaults belong to the **Tencent CodeBuddy case study**, not the framework | The whole Read/Edit/Bash table, including "Self-defined", sits inside the case study (pp.30–31) |
| g020 | "no fines in the corpus" → "no enforcement decisions (companies or amounts)"; notes the PDPC's general penalty power | PDPA Key Concepts pp.154–155 states the maximum penalty, but names no case |

Unchanged after checking: g002, g003, g004, g006, g007, g009, g011, g013, g014, g017, g019.
g019 was re-confirmed: the corpus mentions the EU AI Act (GenAI MGF pp.18, 24; a MindForge case study) but never its penalties.

**Effect on eval-run-001:** it was scored against the earlier wording. The changes are
small, but for a clean comparison re-run the eval as `eval-run-002` before relying on
per-entry scores for g005, g008, g010, g012, g015, g016, g018 and g020.
