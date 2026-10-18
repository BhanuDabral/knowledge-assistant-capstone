# Stakeholder Mapping Worksheet (template)

> Recreated from the W5 lab guide (Step 1), because the course bundle file
> `AI-RAG_W5_stakeholder_map_template.md` was not available. Fill a copy at
> `docs/adr/0001-stakeholder-map.md`; leave this template unchanged.

**Capstone:** _<one line>_
**Author:** _<name>_ · **Date:** _<dd/mm/yyyy>_ · **Status:** Draft → Locked (M1)

Aim for 400–500 words in total. Most of it belongs in prompts 1 and 5.

---

## 1. Primary user — who exactly?

Name a **role + context**, not just a role.

> Bad: "HR team."
> Good: "HR business partners during quarterly performance review cycles."
> Good: "Engineering managers running 1:1s with reports who hit policy questions."

_Your answer:_

## 2. Secondary stakeholders — who else has skin in this?

Include at least one **gatekeeper** (Security, Compliance, Legal) and one role
**whose work is augmented** — the two most often forgotten.

> Example: "Compliance (gatekeeper: signs off before rollout) · HR operations
> (augmented: fewer repeat questions) · IT Security (gatekeeper: data access)."

| Stakeholder | Type (gatekeeper / augmented / sponsor / other) | What they care about |
|---|---|---|
| | | |

## 3. Before-AI workflow — how is this solved today?

Be concrete about **time**.

> Not a number: "Takes a while."
> A number: "~5 minutes per question, ~3 questions per 1:1, ~6 hours per manager per month."

_Your answer:_

## 4. Desired after-state — what changes?

> Example: "Managers get a sourced answer in under 30 seconds and only escalate
> the ~10% of questions the assistant declines."

_Your answer:_

## 5. Top 3 sponsor metrics — what does the sponsor measure?

All three must be **measurable**. "User satisfaction" without a measurement
plan is a vibe, not a metric.

> Example: "Median time-to-answer (target < 30 s, measured from API logs)."

| # | Metric | How it is measured | M1 value | Target (W12 / DR #2) |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
