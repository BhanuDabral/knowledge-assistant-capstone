"""tests/test_critic_creator.py — loop control + no answer-key leakage (W5 Step 5). Offline."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.eval import critic_creator as cc
from src.eval.judge import JudgeScore

IDEAL = "SECRET-IDEAL-FACTS"


def _score(a, g, f):
    return JudgeScore(accuracy=a, groundedness=g, format=f, reasoning="judge reasoning here")


async def _run(scores, max_rounds=3):
    creator = AsyncMock(side_effect=[(f"answer {i}", 0.0) for i in range(1, 5)])
    critic = AsyncMock(return_value=cc.Critique(issues=["missing X"], is_good_enough=False))
    judge = AsyncMock(side_effect=scores)
    with patch.object(cc, "creator", creator), patch.object(cc, "critic", critic), patch.object(cc, "judge_one", judge):
        result = await cc.critic_creator("Q?", IDEAL, system_prompt="SP", max_rounds=max_rounds, log=lambda *_: None)
    return result, creator, critic, judge


@pytest.mark.asyncio
async def test_stops_as_soon_as_the_judge_mean_reaches_threshold():
    result, creator, critic, _ = await _run([_score(2, 2, 3), _score(4, 3, 4)])
    assert [r["round"] for r in result["rounds"]] == [1, 2] and result["converged"]
    assert critic.call_count == 1 and creator.call_count == 2


@pytest.mark.asyncio
async def test_gives_up_after_max_rounds_without_a_wasted_final_critique():
    result, creator, critic, _ = await _run([_score(1, 1, 3)] * 3)
    assert len(result["rounds"]) == 3 and not result["converged"]
    assert critic.call_count == 2 and creator.call_count == 3


@pytest.mark.asyncio
async def test_ideal_answer_never_reaches_critic_or_creator():
    _, creator, critic, judge = await _run([_score(2, 2, 3), _score(4, 4, 4)])
    for call in creator.call_args_list + critic.call_args_list:
        assert IDEAL not in repr(call)
    assert all(IDEAL in repr(c) for c in judge.call_args_list)     # only the judge sees it


@pytest.mark.asyncio
async def test_creator_revision_prompt_contains_previous_answer_and_issues():
    create = AsyncMock(return_value=SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=" revised "))], usage=None))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    text, _ = await cc.creator("Q?", system_prompt="SP", previous="old answer",
                               critique=cc.Critique(issues=["wrong list"], is_good_enough=False), client=client)
    user = create.call_args.kwargs["messages"][1]["content"]
    assert text == "revised" and "old answer" in user and "- wrong list" in user
