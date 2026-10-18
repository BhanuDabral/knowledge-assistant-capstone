"""tests/test_judge.py — judge schema + parsing (W5 Step 3). Offline: no API key, no cost."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from src.eval.judge import (JUDGE_MODEL, JUDGE_TOOL, RUBRIC_PROMPT, JudgeScore, build_messages,
                            judge_one, parse_tool_call)


def _resp(args, prompt_tokens=1000, completion_tokens=100, tool=True):
    calls = [SimpleNamespace(function=SimpleNamespace(arguments=json.dumps(args)))] if tool else None
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=calls))],
                           usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens))


GOOD = {"accuracy": 4, "groundedness": 3, "format": 4, "reasoning": "Lists all four FEAT principles correctly."}


def test_rubric_is_long_enough_and_forces_the_tool():
    assert len(RUBRIC_PROMPT.split()) > 150
    assert "ALWAYS call the rate_answer tool" in RUBRIC_PROMPT


@pytest.mark.parametrize("dim", ["ACCURACY", "GROUNDEDNESS", "FORMAT"])
def test_every_dimension_has_four_anchored_levels(dim):
    section = RUBRIC_PROMPT.split(dim, 1)[1]
    assert all(f"  {n} = " in section for n in (4, 3, 2, 1))


def test_judge_model_is_the_strong_one():
    assert JUDGE_MODEL == "gpt-4o"


def test_tool_schema_requires_all_fields_with_1_to_4_range():
    p = JUDGE_TOOL["function"]["parameters"]
    assert set(p["required"]) == {"accuracy", "groundedness", "format", "reasoning"}
    assert all(p["properties"][d]["minimum"] == 1 and p["properties"][d]["maximum"] == 4
               for d in ("accuracy", "groundedness", "format"))


@pytest.mark.parametrize("bad", [{"accuracy": 5}, {"format": 0}, {"reasoning": "ok"}])
def test_judgescore_rejects_out_of_range_or_empty(bad):
    with pytest.raises(ValidationError):
        JudgeScore(**{**GOOD, **bad})


def test_build_messages_puts_rubric_in_system_and_all_three_texts_in_user():
    m = build_messages("Q?", "IDEAL", "CAND")
    assert m[0] == {"role": "system", "content": RUBRIC_PROMPT}
    assert all(s in m[1]["content"] for s in ("QUESTION:\nQ?", "IDEAL ANSWER:\nIDEAL", "CANDIDATE ANSWER:\nCAND"))


def test_parse_tool_call_builds_score_and_cost():
    s = parse_tool_call(_resp(GOOD))
    assert (s.accuracy, s.groundedness, s.format) == (4, 3, 4)
    assert s.mean == pytest.approx(11 / 3)
    assert s.cost_usd == pytest.approx((1000 * 2.50 + 100 * 10.00) / 1e6)


def test_parse_tool_call_without_tool_raises():
    with pytest.raises(RuntimeError, match="rate_answer"):
        parse_tool_call(_resp(GOOD, tool=False))


@pytest.mark.asyncio
async def test_judge_one_forces_tool_at_temperature_0():
    create = AsyncMock(return_value=_resp(GOOD))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    s = await judge_one("Q?", "IDEAL", "CAND", client=client)
    kw = create.call_args.kwargs
    assert kw["model"] == "gpt-4o" and kw["temperature"] == 0
    assert kw["tool_choice"]["function"]["name"] == "rate_answer"
    assert s.reasoning.startswith("Lists")


@pytest.mark.asyncio
async def test_judge_one_retries_a_malformed_verdict(monkeypatch):
    monkeypatch.setattr("src.eval.judge.asyncio.sleep", AsyncMock())
    create = AsyncMock(side_effect=[_resp({**GOOD, "accuracy": 7}), _resp(GOOD)])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    s = await judge_one("Q?", "IDEAL", "CAND", client=client)
    assert create.call_count == 2 and s.accuracy == 4
