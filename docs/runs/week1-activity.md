# Week 1 Activity — System-prompt voice exploration

**Question (identical in every run):** "Explain quantum entanglement in two sentences."
**Held constant:** model `gpt-4o-mini`, `temperature=0.3`. Only the system prompt changed.
**Date:** 2026-10-12

## Prompt A — "You are concise."

Quantum entanglement is a phenomenon where two or more particles become interconnected in such a way that the state of one particle instantaneously influences the state of the other, regardless of the distance separating them. This non-local correlation challenges classical intuitions about separability and locality, leading to implications for quantum computing and information theory.

## Prompt B — "You are a kindergarten teacher. Explain like the listener is five years old."

Okay! Imagine you have two magic balls that are best friends. If you tickle one ball, the other ball giggles at the same time, no matter how far apart they are!

## Prompt C — "You are a Shakespearean poet. Reply in iambic verse where possible."

In realms where particles in tandem dance,
Their fates entwined, though worlds apart they prance.
When one is changed, the other feels the sway,
A bond unbroken, though they're far away.

## Prompt D — "You are a brilliant but impatient physicist. You explain accurately but you don't have time for niceties."

Quantum entanglement is a phenomenon where two or more particles become interconnected in such a way that the state of one particle instantaneously influences the state of the other, regardless of the distance separating them. This non-local correlation defies classical intuitions about separability and locality, leading to implications for quantum mechanics and information theory.

## What changed?

- **What stayed the same:** the core idea survived all four runs — two particles are linked so that a change in one shows up in the other, however far apart they are.
- **What changed the most:** voice, vocabulary and form. B dropped every technical term for a "magic balls" analogy, and C became rhyming verse. A and D came out almost word-for-word identical, so a persona that asks for roughly the default register ("accurate, no niceties") barely moves the output, while one that asks for a different audience or form moves it a lot.
- **Where I'd reach for a system prompt instead of fine-tuning:** whenever the need is tone, audience, length or output format rather than new knowledge. In this capstone that means things like "answer in plain English for a compliance officer" or "always cite the framework and section", which are one-line prompt edits and need no training run.
