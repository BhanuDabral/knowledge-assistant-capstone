"""src/eval/critic_creator.py — the Critic-Creator loop (W5 Lab Step 5).

  creator (cheap model)  drafts, then revises using the critique
  critic  (strong model) lists concrete problems + is_good_enough — WITHOUT seeing
                         the golden ideal answer, as in production
  judge   (strong model) scores each round against the ideal — measurement only,
                         never shown to the creator

Design choice: if the critic saw the ideal answer, its critique would leak the
golden facts to the creator and the loop would converge by copying the answer
key. Keeping the critic blind makes the trace show what self-critique can
really fix — and what it can't without retrieval.
"""
from __future__ import annotations

import json
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import BaseModel

from src.eval.judge import JudgeScore, judge_one
from src.pipeline.cost import compute_cost_usd
from src.pipeline.llm import _client
from src.pipeline.settings import Settings

CRITIC_PROMPT = """You are a strict reviewer of answers about Singapore AI and data governance frameworks \
(IMDA, PDPC, MAS). Review the DRAFT answer to the QUESTION on accuracy (are the named frameworks, lists, \
conditions and figures right?), groundedness (anything that looks invented or unverifiable?) and format \
(direct, 2-4 sentences, names the framework). List concrete, fixable issues — not "make it better". If you \
are unsure whether a specific claim is in the framework, say so as an issue. Set is_good_enough true only if \
you would let a compliance analyst quote it. ALWAYS call the critique tool."""

CRITIC_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "critique",
        "description": "Return the problems with the draft and whether it is good enough to stop.",
        "parameters": {
            "type": "object",
            "properties": {
                "issues": {"type": "array", "items": {"type": "string"}},
                "is_good_enough": {"type": "boolean"},
            },
            "required": ["issues", "is_good_enough"],
        },
    },
}


class Critique(BaseModel):
    issues: list[str]
    is_good_enough: bool
    cost_usd: float = 0.0


def _cost(model: str, resp) -> float:
    u = resp.usage
    return compute_cost_usd(model, u.prompt_tokens, u.completion_tokens) if u else 0.0


async def creator(question: str, *, system_prompt: str, model: str = "gpt-4o-mini",
                  previous: str | None = None, critique: Critique | None = None,
                  client: AsyncOpenAI | None = None) -> tuple[str, float]:
    """Draft an answer, or revise `previous` to address the critique's issues."""
    client = client or _client(Settings(model=model))
    user = question
    if previous is not None and critique is not None:
        issues = "\n".join(f"- {i}" for i in critique.issues) or "- (none)"
        user = (f"QUESTION:\n{question}\n\nYOUR PREVIOUS ANSWER:\n{previous}\n\nREVIEWER'S ISSUES:\n{issues}\n\n"
                "Rewrite the answer to fix these issues. Reply with the answer text only.")
    resp = await client.chat.completions.create(
        model=model, temperature=0,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content.strip(), _cost(model, resp)


async def critic(question: str, draft: str, *, model: str = "gpt-4o",
                 client: AsyncOpenAI | None = None) -> Critique:
    """Concrete issues + is_good_enough. Does NOT receive the ideal answer."""
    client = client or _client(Settings(model=model))
    resp = await client.chat.completions.create(
        model=model, temperature=0,
        messages=[{"role": "system", "content": CRITIC_PROMPT},
                  {"role": "user", "content": f"QUESTION:\n{question}\n\nDRAFT:\n{draft}"}],
        tools=[CRITIC_TOOL],
        tool_choice={"type": "function", "function": {"name": "critique"}},
    )
    calls = resp.choices[0].message.tool_calls or []
    if not calls:
        raise RuntimeError("critic did not call the critique tool")
    return Critique(**json.loads(calls[0].function.arguments), cost_usd=_cost(model, resp))


async def critic_creator(question: str, ideal_answer: str, *, system_prompt: str,
                         creator_model: str = "gpt-4o-mini", judge_model: str = "gpt-4o",
                         max_rounds: int = 3, threshold: float = 3.5, log=print) -> dict:
    """Run the loop; stop when the judge's mean score reaches `threshold` or after max_rounds."""
    rounds: list[dict] = []
    answer, cost = await creator(question, system_prompt=system_prompt, model=creator_model)
    for n in range(1, max_rounds + 1):
        score: JudgeScore = await judge_one(question, ideal_answer, answer, model=judge_model)
        converged = score.mean >= threshold
        crit = None if converged or n == max_rounds else await critic(question, answer, model=judge_model)
        rounds.append({"round": n, "answer": answer, "score": score.model_dump(), "mean": round(score.mean, 2),
                       "critique": crit.model_dump() if crit else None, "creator_cost_usd": cost})
        log(f"  Round {n}: a={score.accuracy} g={score.groundedness} f={score.format} (mean={score.mean:.2f})"
            + ("  ·  ✓ CONVERGED" if converged else "")
            + (f"  ·  critic: {len(crit.issues)} issues, good_enough={crit.is_good_enough}" if crit else ""))
        if converged or crit is None:
            break
        answer, cost = await creator(question, system_prompt=system_prompt, model=creator_model,
                                     previous=answer, critique=crit)
    total = sum(r["creator_cost_usd"] + r["score"]["cost_usd"] + (r["critique"] or {}).get("cost_usd", 0)
                for r in rounds)
    return {"rounds": rounds, "converged": rounds[-1]["mean"] >= threshold, "final_answer": rounds[-1]["answer"],
            "total_cost_usd": total}


def render_trace(gid: str, entry, result: dict, *, creator_model: str, judge_model: str,
                 max_rounds: int, threshold: float, system_prompt_file: str) -> str:
    """The round-by-round trace as markdown, ending with a Reflection placeholder."""
    out = [f"# Critic-Creator trace — {gid}", "",
           f"**Question:** {entry.question}", "",
           f"**Bucket:** {entry.bucket} · **Creator:** {creator_model} (system prompt `{system_prompt_file}`) · "
           f"**Critic + judge:** {judge_model} · **Max rounds:** {max_rounds} · **Converge at:** judge mean ≥ {threshold}", "",
           "The critic does **not** see the ideal answer (no leakage); the judge scores each round "
           "against it for measurement only.", "",
           f"**Ideal answer (judge only):** {entry.ideal_answer}", ""]
    for r in result["rounds"]:
        s = r["score"]
        out += [f"## Round {r['round']} — a={s['accuracy']} g={s['groundedness']} f={s['format']} (mean {r['mean']})", "",
                "**Answer**", "", "> " + r["answer"].replace("\n", "\n> "), "",
                f"**Judge (vs ideal):** {s['reasoning']}", ""]
        if r["critique"]:
            c = r["critique"]
            out += [f"**Critic (blind)** — good enough: {c['is_good_enough']}", ""]
            out += [f"- {i}" for i in c["issues"]] + [""]
    status = "converged" if result["converged"] else "did not converge"
    out += [f"## Outcome — {status} after {len(result['rounds'])} round(s); "
            f"total cost ${result['total_cost_usd']:.6f}", "",
            "## Reflection", "", "_<your 3-5 sentences: did it improve? real catches vs false alarms? "
            "would you trust this loop in production on this question type?>_", ""]
    return "\n".join(out)


def write_trace(path: str | Path, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")
