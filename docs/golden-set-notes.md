# Golden set notes — `data/golden_set.jsonl`

**Date:** 18/10/2026 · **Author:** Bhanu Dabral · **Entries:** 20

> **Drafted by Claude Code — review and reword.** The questions are yours (W2
> `data/capstone_questions.csv`), unchanged except the two new edge entries.
> The **ideal answers were drafted by Claude Code from the source PDFs** and
> must be checked by you against the cited pages before you defend this set
> at DR #1 (see the checklist at the end).

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

**[YOU: confirm]** Honest ranking against the deck's scale (real users >
domain expert > you at the keyboard): these 18 questions were written by you
in W2 while reading the documents, so they sit at **"you at the keyboard,
reading the source"** — better than invented, weaker than real user
questions. The two edge questions were written by Claude Code. The ideal
answers were drafted by Claude Code from the cited pages. A stronger set would
add questions from a real compliance analyst (your primary user in the
Stakeholder Map).

## Hardest to write

**[YOU: your own paragraph]** Suggested points: the edge cases were hardest
because they had to be checked against all 15 documents (the EU AI Act *is*
mentioned in two of them); and g017 showed that your own question can carry a
wrong premise, which is itself worth testing.

## Ideal-answer review checklist (do this before DR #1)

For each entry, open the PDF at the cited page and tick when the ideal answer
says nothing the page doesn't:

- [ ] g001 – g005
- [ ] g006 – g010
- [ ] g011 – g014
- [ ] g015 – g018 (harder: check every clause)
- [ ] g019 – g020 (edge: confirm the corpus really doesn't answer them)
