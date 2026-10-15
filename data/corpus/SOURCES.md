# Capstone corpus — sources

The 15 public documents behind the knowledge assistant: Singapore AI & data governance from **IMDA, PDPC, the AI Verify Foundation and MAS**. The PDF files themselves are **not** in this repository (it is public): they live locally in `data/corpus/raw/`, which is gitignored. Download each one from the official URL below to reproduce the corpus.

- **Publisher:** the agency that hosts the document on its official site.
- **Version / date:** taken from the PDF's own cover or first page.
- **Pages:** page count of the local copy.
- **Used by:** questions in `data/capstone_questions.csv` that this document is the proposed source for.

| # | Document | Publisher | Version / date (from the PDF) | Pages | Local file (`data/corpus/raw/`) | Official URL | Used by |
|---|---|---|---|---|---|---|---|
| 1 | Advisory Guidelines on Key Concepts in the PDPA | PDPC | Issued 23 Sep 2013, revised 29 Apr 2026 | 165 | `Advisory Guidelines on Key Concepts in the PDPA_Apr2026.pdf` | [pdpc.gov.sg](https://www.pdpc.gov.sg/organisations/regulations-decisions/regulatory-guidance/advisory-guidelines-on-key-concepts-in-the-personal-data-protection-act) ¹ | Q4, Q11 |
| 2 | Advisory Guidelines on Use of Personal Data in AI Recommendation and Decision Systems | PDPC | Issued 1 Mar 2024 | 21 | `Advisory Guidelines on the Use of Personal Data in AI Recommendation and Decision Systems.pdf` | [pdpc.gov.sg](https://pdpc.gov.sg/guidelines-and-consultation/2024/02/advisory-guidelines-on-use-of-personal-data-in-ai-recommendation-and-decision-systems) | Q3, Q12, Q18 |
| 3 | Guide to Data Protection Practices for ICT Systems | PDPC | Issued 14 Sep 2021, revised 20 Jul 2026 | 58 | `guide-to-data-protection-practices-for-ict-systems.pdf` | [pdpc.gov.sg](https://www.pdpc.gov.sg/organisations/resources/guidance-by-topic/guide-to-data-protection-practices-for-ict-systems) | Q15 |
| 4 | Model AI Governance Framework for Generative AI | AI Verify Foundation & IMDA | 2024 (file dated 19 Jun 2024) | 36 | `Model-AI-Governance-Framework-for-Generative-AI-19-June-2024.pdf` | [aiverifyfoundation.sg](https://aiverifyfoundation.sg/wp-content/uploads/2024/06/Model-AI-Governance-Framework-for-Generative-AI-19-June-2024.pdf) | Q8 |
| 5 | Model AI Governance Framework for Agentic AI | IMDA | Version 1.5, published 20 May 2026, updated 5 Jun 2026 | 53 | `Mgf for Agentic AI (atx Release) July 2026.pdf` | [imda.gov.sg](https://www.imda.gov.sg/-/media/imda/files/about/emerging-tech-and-research/artificial-intelligence/mgf-for-agentic-ai.pdf) | Q5, Q6, Q13, Q14, Q19 |
| 6 | Starter Kit for Testing LLM-Based Applications for Safety and Reliability | IMDA | Version 1.0, Jan 2026 | 109 | `large-language-model-starter-kit.pdf` | [imda.gov.sg](https://www.imda.gov.sg/-/media/imda/files/about/emerging-tech-and-research/artificial-intelligence/starter-kit-for-testing-llm-based-applications-for-safety-and-reliability.pdf) | — |
| 7 | Principles to Promote FEAT in the Use of AI and Data Analytics in Singapore's Financial Sector | MAS | 2018 | 15 | `FEAT Principles Final.pdf` | [mas.gov.sg](https://www.mas.gov.sg/publications/monographs-or-information-paper/2018/FEAT) | Q1, Q2 |
| 8 | Veritas Document 3A — FEAT Fairness Principles Assessment Methodology | MAS (Veritas Consortium) | 2022 | 71 | `Veritas Document 3A - FEAT Fairness Principles Assessment Methodology.pdf` | [mas.gov.sg](https://www.mas.gov.sg/-/media/MAS-Media-Library/news/media-releases/2022/Veritas-Document-3A---FEAT-Fairness-Principles-Assessment-Methodology.pdf) | Q10 |
| 9 | Veritas Document 3C — FEAT Transparency Principles Assessment Methodology | MAS (Veritas Consortium) | 2022 | 45 | `Veritas Document 3C - FEAT Transparency Principles Assessment Methodology.pdf` | [mas.gov.sg](https://www.mas.gov.sg/-/media/mas-media-library/news/media-releases/2022/veritas-document-3c---feat-transparency-principles-assessment-methodology.pdf) | Q17 |
| 10 | Guidelines on Artificial Intelligence Risk Management | MAS | 7 Oct 2026 | 30 | `Guidelines on Artificial Intelligence Risk Management.pdf` | [mas.gov.sg](https://www.mas.gov.sg/-/media/mas-media-library/regulation/guidelines/bd/guidelines-on-artificial-intelligence-risk-management-for-financial-institutions/guidelines-on-artificial-intelligence-risk-management.pdf) | — |
| 11 | AI Risk Management: Executive Handbook (Project MindForge) | MAS / MindForge Consortium | Nov 2025 | 26 | `MindForge AI Risk Management Executive Handbook.pdf` | [mas.gov.sg](https://www.mas.gov.sg/-/media/mas-media-library/schemes-and-initiatives/ftig/project-mindforge/mindforge-ai-risk-management-executive-handbook.pdf) | — |
| 12 | AI Risk Management: Operationalisation Handbook (Project MindForge) | MAS / MindForge Consortium | Jan 2026 | 173 | `MindForge AI Risk Management Operationalisation Handbook.pdf` | [mas.gov.sg](https://www.mas.gov.sg/-/media/mas-media-library/schemes-and-initiatives/ftig/project-mindforge/mindforge-ai-risk-management-operationalisation-handbook.pdf) | Q9, Q16, Q20 |
| 13 | Safeguards for Agentic Finance at Runtime (SAFR) white paper | MAS | **Version 1.1, Oct 2026** ² | 29 | `SAFR v1.1.pdf` | [mas.gov.sg](https://www.mas.gov.sg/-/media/mas-media-library/development/fintech/ai-safr/safr-v1-1.pdf) | Q7, Q19 |
| 14 | Guidelines on Fair Dealing — Board and Senior Management Responsibilities (FSG-G04) | MAS | May 2024 (effective 30 May 2024) | 40 | `Fair Dealing Guidelines 30 May 2024.pdf` | [mas.gov.sg](https://www.mas.gov.sg/-/media/mas-media-library/fair-dealing-guidelines-30-may-2024.pdf) | — |
| 15 | Notice FSM-N05 — Technology Risk Management (banks) | MAS | Issued 9 May 2024 | 3 | `MAS Notice FSM-N05.pdf` | [mas.gov.sg](https://www.mas.gov.sg/regulation/notices/notice-fsm-n05) ³ | — |

**Total:** 15 documents, 874 pages, about 30 MB. All 15 have a text layer, so no OCR is needed for chunking in W7.

## Notes
1. The local copy says *revised 29 April 2026*. The PDPC page is the official home of these guidelines, but this revision date was not confirmed on it at the time of writing; check the page's "last updated" note.
2. The corpus uses **SAFR v1.1** (Oct 2026), downloaded from MAS on 2026-10-15. The earlier **v1.0** (Jul 2026, 25 pages, <https://www.mas.gov.sg/-/media/mas-media-library/development/fintech/ai-safr/safr.pdf>) is kept locally as `SAFR.pdf` for comparison. Exclude it when chunking in W7 so the two versions don't compete in retrieval.
3. MAS consulted in 2026 on proposed amendments to the technology risk management notices, FSM-N05 included. The corpus holds the 9 May 2024 notice.
4. Five documents (#6, #10, #11, #14, #15) are not the proposed source for any current question. They stay in the corpus as realistic "distractor" content for retrieval, or can get questions of their own later.
