# Prompt pairwise 001 — v1 vs v2 (refusal rule)

**Date:** 18/10/2026 · **Golden set:** 20 entries · **Candidate:** gpt-4o-mini via `ask_llm` (the `/ask_batched` path)
**Judge:** gpt-4o, both orders per question · **Raw results:** `data/pairwise-001-results.json`

## What changed

v1 — `data/prompt-v1.txt` (the structured pattern from the deck; CONTEXT and
EXAMPLES are **deliberately skipped**: no retrieval until W6, and no worked
examples yet):

```
ROLE: You are a knowledge assistant on Singapore AI and data governance frameworks published by IMDA, PDPC and MAS.
TASK: Answer the user's question in plain English.
FORMAT: 2-4 sentences (a short list is fine for enumerations), naming the framework or document the answer comes from. Return it through the answer_question tool.
```

v2 — `data/prompt-v2.txt` = v1 plus **one line, the single change tested**:

```
If you are not certain that the answer is stated in an IMDA, PDPC or MAS publication, say that you don't know and name the publication the user should check, instead of guessing.
```

How it's applied: `Settings.system_prompt_file` (env `PIPELINE_SYSTEM_PROMPT_FILE`).
Server-side only — API callers can't send a prompt. Unset = no system prompt (W4 behaviour, used for eval-run-001).

## Aggregate result

```
v1 wins      : 1
v2 wins      : 8
tie          : 4
ambiguous    : 7  (forward/reverse disagreed — position bias on these)
position-bias rate : 7/20  =  35%
cost (candidates + judge) : $0.003835 + $0.088167
wall-clock   : 15.6s
```

**The 35% is above the guide's 25% "investigate first" line, so I did.** The 7
ambiguous rows are two different things:

- **4 true order flips (20%)** — the slot shown first won in both orders on g003,
  g008, g012 (the judge's reasoning literally starts "The FIRST candidate…" both
  times), and the second slot on g013. These are near-identical answers where
  the judge had no real preference — exactly the deck's position bias.
- **3 tie-vs-winner splits** (g002, g006, g020). One of them is a **judge
  error**: on g002 the forward verdict says v1 "correctly identifies the Business
  Improvement and Research Exceptions" — v1 mentions neither. The reverse order
  said "tie", so the flip turned a judge mistake into "ambiguous" instead of a
  false v1 win.

So the flip-and-aggregate habit protected the result twice: from order effects
and from a hallucinating judge.

## Findings

**Where v2 won, and why.**
- **g019 (edge, EU AI Act fines):** v1 quoted "€30 million or 6%" from memory; v2
  said "I don't know … check the EU AI Act". This is the change working exactly
  as intended.
- **g015–g018 (all four harder):** v2 won every one, but by being *closer*, not
  by declining — e.g. g015 "must operate within the bounds defined by the user"
  vs v1's vaguer "designed purpose".
- **g001:** v1 introduced a wrong principle ("Robustness"); v2 listed FEAT correctly.

**Where v1 won.** g011 — v1 described "frequency of override actions" and
"time taken to review" (close to the ideal); v2 invented "review requests vs
volume". Same model, different sampling.

**What did *not* change — the important finding.** v2 declined on only **2 of
20** (the two edge questions). On the document-specific happy-path questions it
**still invented lists** (g004 four dimensions, g006 nine dimensions, g014 roles
— all ties because both versions were wrong). The model is "certain" about
answers it is making up, so a refusal instruction cannot catch them. v2 also
still invents sources ("IMDA's Cloud Computing…" on g012).

## Decision

**Decision (18/10/2026): ship v2** as the default system
prompt — 8 wins to 1, it fixes the one behaviour ADR 0001 cares most about (no
confident answers outside the corpus), and it costs ~30 extra input tokens.
Enable it with `PIPELINE_SYSTEM_PROMPT_FILE=data/prompt-v2.txt` in `.env`.
But do **not** claim it fixes hallucination: on in-scope questions the gap is
missing knowledge, which only retrieval (W6+) can supply. Next pairwise
candidate after W6: v3 = v2 + "answer only from the CONTEXT block".

**After shipping (eval-run-003):** with v2 live, g020 declined but g019 quoted a fine again, so
the refusal is probabilistic, not guaranteed. See `docs/eval-run-003.md`.
