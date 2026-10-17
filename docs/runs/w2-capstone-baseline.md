# Capstone baseline: your 20 questions, answered without retrieval

**What this is:** the 20 capstone questions in `data/capstone_questions.csv`, written for the 15-document IMDA / PDPC / MAS corpus (see `data/corpus/SOURCES.md`). They were run through the Week 2 pipeline against the real OpenAI API with **no retrieval**: `gpt-4o-mini` answers from its training data alone.

**Why:** this records a *before-RAG* reference. W7 chunks the corpus and W11 adds retrieval; re-run the same CSV then and compare answer by answer. Each question already names its proposed source document (and page, where confirmed), so the comparison can be checked against the documents.

- **Run:** `results.db` run 14, 2026-10-15, 20 questions in 25.33 s, 0 retries, `use_fake=false`
- **Full output:** [`w2-capstone-baseline.json`](w2-capstone-baseline.json)
- **Re-run:**
  ```bash
  python -m src.pipeline.pipeline --questions data/capstone_questions.csv
  ```
  This overwrites `results.json`. Copy it here first, then `git checkout -- results.json`.
- **Earlier draft:** run 13 used a placeholder question set written before your questions existed. It stays in `results.db` as history only.

## Graded against the source documents (7 of 20)

These 7 questions have a confirmed source page in the corpus. The model's answer was read against that page.

| Q | Question (short) | Source (PDF page) | Verdict | What the source says vs. the model |
|---|---|---|---|---|
| 1 | Four FEAT principles (MAS 2018) | FEAT Principles Final, p6 | ✅ Correct | Fairness, Ethics, Accountability, Transparency, all four named |
| 4 | Four conditions for the PDPA Research Exception | Key Concepts in the PDPA, p74 | ❌ Wrong | Source: (a) purpose needs identifiable data, (b) clear public benefit, (c) results not used for decisions affecting the individual, (d) published results don't identify the individual. Model: generic advice ("purpose limitation", "minimal identifiability", …), none of the four |
| 8 | Nine dimensions of the GenAI framework (2024) | MGF for GenAI, p2 | ❌ Wrong | Source: Accountability, Data, Trusted Development and Deployment, Incident Reporting, Testing and Assurance, Security, Content Provenance, Safety and Alignment R&D, AI for Public Good. Model admits it lacks the document, then invents dimensions (Transparency, Fairness, User-Centricity, …) |
| 11 | Part 9B offences for egregious mishandling | Key Concepts in the PDPA, p9 | ⚠️ Partial | Source: knowing or reckless unauthorised (a) disclosure, (b) use for wrongful gain or loss, (c) re-identification of anonymised data. Model: has disclosure, blurs (b), misses (c), adds non-offences such as "failure to protect" |
| 13 | Two indicators for rubber-stamping / review fatigue | MGF for Agentic AI, p30 | ⚠️ Partial | Source: human override rate, and human response times. Model: a "change ratio" and "time spent on review", close in spirit but not the framework's indicators |
| 14 | Default approvals for Read / Edit / Bash | MGF for Agentic AI, p31 | ⚠️ Partial | Source: Read needs no approval; Edit needs approval valid for that session only; Bash needs approval, permanent per project or command. Model: roughly right on Read and Edit, but generic and missing the session vs. permanent scoping |
| 15 | Encryption for long-term retention in ICT systems | Guide to Data Protection Practices for ICT Systems, p25 | ✅ Correct | Source: AES with a key length of at least 256 bits. Model: AES-256 (it also adds RSA and ECC, which the source does not mention) |

**Score on the graded 7:** 2 correct, 3 partial, 2 wrong. The two outright failures are where the answer is a specific list that lives only in the document, which is exactly what retrieval is for.

## Still to grade (13 of 20)
Q2, Q3, Q5, Q6, Q7, Q9, Q10, Q12, Q16, Q17, Q18, Q19 and Q20 have a proposed source document but no confirmed page yet. Grade them while building the corpus (W7), and add the page to `source_pages` in `data/capstone_questions.csv` as you go.

## Next
- [ ] W7: chunk the corpus (exclude the superseded `SAFR.pdf` v1.0; see SOURCES.md)
- [ ] W11: re-run this CSV with retrieval and compare with this file
- [ ] W18: turn the graded answers into an evaluation set


