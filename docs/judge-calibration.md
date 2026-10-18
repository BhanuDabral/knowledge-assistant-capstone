# Judge Calibration

> **STATUS: SCORED 18/10/2026** (blind, offline, by Bhanu). Findings below drafted by Claude Code from
> these scores and the judge's reasoning — confirm or reword the Decision.

**Date:** 18/10/2026 (scored offline from W5_Judge_Calibration_Review.pptx) · **Cohort member:** Bhanu Dabral
**Capstone:** Singapore AI & Data Governance Assistant
**Sampled entries (10 of 20, stratified 6 happy / 3 harder / 1 edge):** g002, g003, g006, g009, g010, g013, g016, g017, g018, g019

> Prepared by Claude Code: the sample and the texts below. **The scores are yours to give, blind.**
> Do this BEFORE you read the per-entry table in `docs/eval-run-001.md` or the evidence deck.
> The sample avoids the entries whose judge scores were already mentioned to you (g001, g008, g012, g020).
> Use the same rubric as the judge: `RUBRIC_PROMPT` in `src/eval/judge.py` (1-4 per dimension).

## My scores (filled in blind — without looking at the judge)

| Golden id | My accuracy | My groundedness | My format | One-line note |
|---|---|---|---|---|
| g002 | 1 | 1 | 4 | Omits both exceptions and substitutes unsupported legal sections. |
| g003 | 2 | 2 | 4 | Reverses identifiable-data condition and misplaces the consent test. |
| g006 | 1 | 1 | 4 | Only Data matches. The remaining eight dimensions are invented. |
| g009 | 2 | 2 | 4 | Omits mental state/re-identification and adds unsupported offences. |
| g010 | 2 | 2 | 2 | Generic compliance list misses the AI training-data practices. |
| g013 | 2 | 3 | 2 | Generic distinction misses FEAT P12–14 and instance specificity. |
| g016 | 2 | 3 | 4 | Definitions broadly right. Missing governance unit is substantive. |
| g017 | 2 | 2 | 4 | Accepts false three-item premise and substitutes consumer rights. |
| g018 | 2 | 3 | 2 | Missing approval duration, case-study attribution and precise defaults. |
| g019 | 1 | 1 | 4 | States unsupported figures instead of abstaining and referring to EU sources. |

When done, run:

```bash
python scripts/compute_calibration.py --calibration-file docs/judge-calibration.md --db data/answers.db --label eval-run-001
```

## Findings

> Drafted by Claude Code from your scores and the judge's reasoning in `eval_runs` — review and reword.

### Agreement (`scripts/compute_calibration.py`, label eval-run-001)

- **Exact: 15 / 30 (50%)** · **Within-1: 29 / 30 (97%)**
- Per dimension, exact: accuracy 7/10 · groundedness 5/10 · format 3/10
- Course band: exact 50–70% with within-1 ≥ 90% → *rubric has ambiguity at the level boundaries; sharpen once, then trust.* (50% is at the bottom edge of that band.)

| id | accuracy (me / judge) | groundedness | format |
|---|---|---|---|
| g002 | 1 / 1 | 1 / 1 | 4 / 3 |
| g003 | 2 / 2 | 2 / 2 | 4 / 4 |
| g006 | 1 / 1 | 1 / 1 | 4 / 4 |
| g009 | 2 / 1 | 2 / 1 | 4 / 3 |
| g010 | 2 / 1 | 2 / 2 | 2 / 3 |
| g013 | 2 / 2 | 3 / 2 | 2 / 3 |
| g016 | 2 / 2 | 3 / 2 | 4 / 4 |
| g017 | 2 / 1 | 2 / 1 | 4 / 3 |
| g018 | 2 / 2 | 3 / 2 | 2 / 3 |
| g019 | 1 / 1 | 1 / 1 | **4 / 1** |

### Disagreements > 1 (the one worth investigating)

- **g019 (format: 4 vs 1, Δ=3):** the judge wrote "the format is unusable as it provides incorrect
  information instead of declining". That is a content judgement scored as format. **Verdict: rubric
  ambiguity** — the format anchors never say format is judged independently of correctness.

### Patterns in the Δ=1 disagreements

- **Format (7 of 10 differ):** the judge mixes content into format ("format acceptable, but content
  misleading" → 3), while I scored usability alone; I also marked generic or padded answers (g010,
  g013, g018) as 2 where the judge gave 3. **Rubric ambiguity** at 2 vs 3 and on what format covers.
- **Groundedness (g013, g016, g018: me 3, judge 2):** the judge treats generic filler ("building
  trust", "organizational policies", "data pipelines and hardware") as invented specifics; I treated it
  as harmless context. **Rubric ambiguity** at the 3 vs 2 boundary.
- **Accuracy and groundedness (g009, g010, g017: me 2, judge 1):** the judge is stricter where some
  facts partly overlap. Boundary 2 vs 1 ("partly right" vs "wrong") is undefined.
- **Direction:** on accuracy and groundedness the judge was **never more lenient than me**; on these
  10 its averages are lower (accuracy 1.4 vs my 1.7, groundedness 1.5 vs 2.0). It did not over-score
  confident hallucinations, the failure mode the course warns about. The eval-run-001 baseline is,
  if anything, slightly harsh — not inflated.

### Decision

- **Confirmed by Bhanu (18/10/2026):** **trust the judge for routine, directional eval runs in W6+** (97% within-1,
  never more lenient on accuracy/groundedness), **after one rubric sharpening**:
  1. FORMAT: "Score usability only, independent of whether the content is correct."
  2. GROUNDEDNESS 3 vs 2: "Generic statements not tied to any document are harmless context (3); a named
     list item, section, figure, framework or source that is not in the ideal is an invented specific (2)."
  3. ACCURACY 2 vs 1: "1 = none of the ideal's facts present (or the main claim contradicts it);
     2 = at least one ideal fact present, others missing or wrong."
- Validate it: re-run as `eval-run-002`, then re-run this script with `--label eval-run-002` on the same
  scores. Exact agreement should rise (format especially); g019 format should no longer be 1.

### Validation — rubric v2 (done 18/10/2026)

Same blind scores, same answers, re-judged with rubric v2 (label `eval-run-001-rubric-v2`):

| | rubric v1 | rubric v2 |
|---|---|---|
| Exact | 15/30 (50%) | **17/30 (57%)** |
| Within-1 | 29/30 (97%) | **30/30 (100%)** |
| Disagreements > 1 | 1 | **0** |
| Exact by dimension (acc / grd / fmt) | 7 / 5 / 3 | 6 / 6 / 5 |

The format fix worked (g019 4 vs 4, g017 4 vs 4). Remaining gaps are ±1 boundary calls: the judge
still treats some generic filler as unsupported (g013, g016, g018), and I mark padded or generic
answers 2 on format where it gives 3. Decision stands: trust the judge for routine, directional runs;
spot-check 2 of every 20; re-calibrate when the golden set grows to 50. Details: `docs/eval-run-002.md`.

---

## The 10 entries to score (question · ideal answer · the app's answer)

### g002

**Question:** Which statutory exceptions under the PDPA allow organizations to process personal data for AI development without fresh consent

**Ideal answer:** The guidelines name two exceptions an AI developer can rely on instead of consent: the Business Improvement Exception (enhancing an existing product, improving operational efficiency, or offering new or personalised products and services; it also covers sharing within a group of companies) and the Research Exception (commercial research to advance science and engineering without a product development roadmap; it also covers sharing between unrelated companies for joint research).

**Candidate (the app's answer in eval-run-001):**

> Under the Personal Data Protection Act (PDPA) in Singapore, several exceptions allow organizations to process personal data for AI development without fresh consent. Notably, the exceptions include necessary processing for the performance of a contract (Section 13), compliance with legal obligations (Section 14), and the legitimate interests of the organization (Section 15), provided that the processing does not override individuals' interests or fundamental rights. Additionally, organizations can process anonymized or de-identified data that cannot be traced back to individuals, which is often used in AI training.
> 
> Sources given: https://www.pdpc.gov.sg; https://www.datalawyer.com.sg

### g003

**Question:** What four conditions must be met to rely on the PDPA's Research Exception

**Ideal answer:** To use personal data under the Research Exception: (a) the research purpose cannot reasonably be accomplished unless the data is in individually identifiable form; (b) there is a clear public benefit to using the data for the research; (c) the results will not be used to make any decision that affects the individual; and (d) if the results are published, they are published in a form that does not identify the individual. Disclosure for research additionally requires that it is impracticable to seek the individual's consent.

**Candidate (the app's answer in eval-run-001):**

> To rely on the Personal Data Protection Act (PDPA)'s Research Exception in Singapore, the following four conditions must be met: 1) The research purpose must be recognized as legitimate and must benefit the public; 2) The data must be anonymized or de-identified to minimize risks to individuals; 3) It must be impracticable to obtain consent from the individuals concerned; and 4) The organization must have appropriate measures in place to ensure data security and protection of the personal data used in research.

### g006

**Question:** What are the nine ecosystem dimensions established in the Model AI Governance Framework for Generative AI (2024)

**Ideal answer:** The nine dimensions are: Accountability; Data; Trusted Development and Deployment; Incident Reporting; Testing and Assurance; Security; Content Provenance; Safety and Alignment R&D; and AI for Public Good.

**Candidate (the app's answer in eval-run-001):**

> The nine ecosystem dimensions outlined in the Model AI Governance Framework for Generative AI (2024) are: 1) Technology and Infrastructure, 2) Data, 3) Algorithms, 4) Human Inputs, 5) Use Cases, 6) Organizations, 7) Policies and Regulations, 8) Societal Aspects, and 9) Continuous Monitoring and Improvement. These dimensions work in concert to ensure responsible development, deployment, and governance of generative AI systems.

### g009

**Question:** Under Part 9B of the PDPA, what specific actions constitute offences for egregious mishandling of personal data by individuals

**Ideal answer:** Part 9B makes it an offence for individuals to knowingly or recklessly: (a) disclose personal data without authorisation; (b) use personal data for a wrongful gain or a wrongful loss to any person; or (c) re-identify anonymised data.

**Candidate (the app's answer in eval-run-001):**

> Under Part 9B of the Personal Data Protection Act (PDPA) in Singapore, specific actions that constitute offences for egregious mishandling of personal data by individuals include unauthorized access, wrongful use or disclosure of personal data, and failure to take appropriate measures to ensure the security and confidentiality of personal data. Additionally, actions that result in reputational harm or significant damage to individuals' interests, such as sharing or selling personal data without consent, are also considered serious offences.
> 
> Sources given: https://www.pdpc.gov.sg/; https://sso.agc.gov.sg/Act/PDPA2012

### g010

**Question:** What good practices are recommended under the PDPA for third-party Service Providers acting as data intermediaries during AI development

**Ideal answer:** Service Providers that process personal data on a customer's behalf act as data intermediaries. The guidelines call it good practice to (a) use data mapping and labelling at the pre-processing stage to track which data formed the training set, and (b) keep a provenance record of the training data's lineage: its source and how it was transformed during preparation. These help detect unauthorised access or changes to training data and help the customer meet its own notification, consent and accountability obligations.

**Candidate (the app's answer in eval-run-001):**

> Under the Personal Data Protection Act (PDPA), third-party service providers acting as data intermediaries during AI development should adhere to several good practices. Key recommendations include ensuring that data processing is conducted only according to the instructions provided by the data owner, implementing robust security measures to protect sensitive data, maintaining transparency about data usage and its purpose, and ensuring compliance with data retention policies. Additionally, service providers should conduct regular assessments and audits to ensure adherence to the PDPA and engage in training programs to foster data protection awareness among their staff.

### g013

**Question:** In the Veritas Transparency Methodology (Document 3C), what is the difference between proactive and reactive transparency

**Ideal answer:** Proactive transparency is the institution telling the general public, including current and prospective customers, that it uses their data and AIDA systems to engage them or make decisions about them (FEAT Principle 12). Reactive (or responsive) transparency is answering a data subject's request about a specific decision that affected them, such as why a loan was declined (FEAT Principles 13 and 14). Proactive transparency can be generic or instance-specific; reactive transparency is always instance-specific.

**Candidate (the app's answer in eval-run-001):**

> Proactive transparency involves actively sharing information with stakeholders before they ask for it, aiming to prevent issues and build trust. This approach emphasizes a culture of openness and accountability, allowing stakeholders to have access to relevant information that can enhance decision-making. In contrast, reactive transparency occurs when information is shared in response to specific inquiries or issues raised by stakeholders. This method typically addresses concerns that have already come to light, focusing on rectifying problems rather than preemptively mitigating them.

### g016

**Question:** How does the MindForge Framework distinguish between an AI "Model", an AI "System", and an AI "Use Case"

**Ideal answer:** A model is a mathematical or logical representation that maps inputs to outputs, such as an LLM predicting tokens or a credit-default model. A system is a model plus the software components that make it usable in the real world, such as a chatbot with a search engine; it may contain several models. A use case is the specific real-world context in which a system is intentionally used, such as underwriting loan risk. The handbook makes the use case the basic unit of AI governance and risk management, because with GenAI and agentic AI a model's risks depend on its use case and its system's guardrails.

**Candidate (the app's answer in eval-run-001):**

> The MindForge Framework distinguishes between three key concepts: an AI "Model", an AI "System", and an AI "Use Case". An AI "Model" refers to the algorithm or mathematical representation that enables the AI to perform specific tasks, such as classification or prediction. An AI "System" encompasses the entire infrastructure and architecture that includes the model, data pipelines, user interfaces, and any necessary hardware or software. An AI "Use Case" defines a specific application or scenario where the AI system is employed to solve a real-world problem, illustrating the practical value and effectiveness of the underlying model and system.

### g017

**Question:** According to PDPA guidelines on AI Recommendation Systems, what three key elements should be included in consumer notifications at the point of data collection

**Ideal answer:** The guidelines list four items, not three, that organisations are encouraged to include in notifications where practicable: (a) the product function that needs personal data (e.g. movie recommendations); (b) a general description of the types of personal data collected (e.g. viewing history); (c) how processing that data is relevant to the product feature; and (d) the specific features of the data most likely to influence the feature (e.g. whether a movie was watched completely). Notifications should be proportionate to the risk and can be layered, for example a pop-up linking to a fuller policy.

**Candidate (the app's answer in eval-run-001):**

> According to the Personal Data Protection Act (PDPA) guidelines regarding AI Recommendation Systems, three key elements that should be included in consumer notifications at the point of data collection are: 1) Purpose of Collection - Clearly inform consumers about the specific purposes for which their personal data is being collected and processed. 2) Data Usage - Explain how the data will be used, particularly in relation to AI recommendations, including any third-party sharing. 3) Rights of Consumers - Notify consumers of their rights under the PDPA, including the right to access their data and the right to withdraw consent for data usage at any time.

### g018

**Question:** What default human approval requirements are recommended for "Read", "Edit", and "Bash" agent actions

**Ideal answer:** In the Tencent CodeBuddy case study in the framework, approval defaults follow the risk of each action: Read (reading files, listing directories) needs no approval; Edit (modifying files) needs approval valid only for that session; and Bash (running shell commands) needs approval that is then permanent for the project or the command. The framework also lets users or organisations adjust these defaults to each project's risk, to avoid alert fatigue.

**Candidate (the app's answer in eval-run-001):**

> For agent actions such as "Read," "Edit," and "Bash," common default human approval requirements are as follows:
> 
> 1. **Read**: Typically, no human approval is required for read actions, as they are generally considered safe and non-intrusive, allowing users to access or view information without altering it.
> 
> 2. **Edit**: Approval is usually required for edit actions, especially when they involve significant changes to documents or systems, as this could lead to unauthorized modifications or data loss.
> 
> 3. **Bash**: This action usually demands strict human approval due to its potential to execute commands that can alter system states, perform deletions, or modify critical configurations, therefore posing a risk to system integrity and security.
> 
> These requirements can vary based on organizational policies and specific risk assessments.

### g019

**Question:** What is the maximum fine under the EU AI Act for using a prohibited AI practice?

**Ideal answer:** This is outside the assistant's corpus, which covers Singapore AI and data governance frameworks (IMDA, PDPC, MAS). The documents mention the EU AI Act only in passing, as a reference point for incident reporting and deepfake transparency, and do not state its penalties. Check the official text of the EU AI Act (Regulation (EU) 2024/1689) or EU sources. The assistant should not guess a figure and does not give legal advice.

**Candidate (the app's answer in eval-run-001):**

> Under the EU AI Act, the maximum fine for using a prohibited AI practice can reach up to €30 million or 6% of the total worldwide annual revenue of the company, whichever is higher. This legislation aims to enforce strict regulations on high-risk AI applications and prohibits certain unacceptable AI practices that could pose significant risks to safety and fundamental rights.
