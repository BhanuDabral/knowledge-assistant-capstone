"""tests/test_pairwise.py — pairwise position-bias logic + versioned system prompt (W5 Step 4). Offline."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.eval.pairwise import _to_label, combine, pairwise_compare
from src.pipeline.llm import ask_llm, system_messages
from src.pipeline.models import Question
from src.pipeline.settings import Settings


def _resp(name, args, pt=500, ct=50):
    call = SimpleNamespace(function=SimpleNamespace(name=name, arguments=json.dumps(args)))
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[call]))],
                           usage=SimpleNamespace(prompt_tokens=pt, completion_tokens=ct))


def _client(*responses):
    create = AsyncMock(side_effect=list(responses))
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), create


@pytest.mark.parametrize("winner, v1_first, label", [
    ("first", True, "v1"), ("second", True, "v2"), ("first", False, "v2"), ("second", False, "v1"), ("tie", False, "tie"),
])
def test_slot_maps_back_to_prompt_version(winner, v1_first, label):
    assert _to_label(winner, v1_first) == label


def test_combine_only_trusts_agreement():
    assert combine("v2", "v2") == "v2" and combine("tie", "tie") == "tie"
    assert combine("v1", "v2") == "ambiguous" and combine("v1", "tie") == "ambiguous"


@pytest.mark.asyncio
async def test_consistent_winner_across_both_orders():
    # forward (v1 first): judge picks "second" = v2; reverse (v2 first): picks "first" = v2
    client, create = _client(_resp("pick_winner", {"winner": "second", "reasoning": "v2 declines honestly"}),
                             _resp("pick_winner", {"winner": "first", "reasoning": "v2 declines honestly"}))
    r = await pairwise_compare("Q", "IDEAL", "ANSWER-V1", "ANSWER-V2", client=client)
    assert r["result"] == "v2" and create.call_count == 2
    # the two calls really swapped the order
    users = [c.kwargs["messages"][1]["content"] for c in create.call_args_list]
    assert users[0].index("ANSWER-V1") < users[0].index("ANSWER-V2")
    assert users[1].index("ANSWER-V2") < users[1].index("ANSWER-V1")
    assert r["cost_usd"] == pytest.approx(2 * (500 * 2.5 + 50 * 10) / 1e6)


@pytest.mark.asyncio
async def test_first_slot_always_winning_is_reported_as_ambiguous():
    client, _ = _client(_resp("pick_winner", {"winner": "first", "reasoning": "first is better"}),
                        _resp("pick_winner", {"winner": "first", "reasoning": "first is better"}))
    r = await pairwise_compare("Q", "IDEAL", "A1", "A2", client=client)
    assert r["result"] == "ambiguous"


def test_no_prompt_file_means_w4_behaviour():
    assert system_messages(Settings(system_prompt_file=None)) == []


def test_prompt_file_becomes_the_system_message(tmp_path):
    p = tmp_path / "prompt.txt"
    p.write_text("ROLE: test\n", encoding="utf-8")
    assert system_messages(Settings(system_prompt_file=p)) == [{"role": "system", "content": "ROLE: test"}]


def test_real_prompt_files_differ_by_one_added_line():
    v1 = Path("data/prompt-v1.txt").read_text().splitlines()
    v2 = Path("data/prompt-v2.txt").read_text().splitlines()
    assert v2[:len(v1)] == v1 and len(v2) == len(v1) + 1 and "don't know" in v2[-1]


@pytest.mark.asyncio
async def test_ask_llm_sends_system_prompt_before_the_question(tmp_path):
    p = tmp_path / "v2.txt"
    p.write_text("SYSTEM PROMPT", encoding="utf-8")
    client, create = _client(_resp("answer_question", {"content": "c", "confidence": 0.5, "sources": []}))
    s = Settings(use_fake=False, model="gpt-4o-mini", openai_api_key="x", system_prompt_file=p)
    with patch("src.pipeline.llm._client", return_value=client):
        await ask_llm(Question(question="What is FEAT?"), s)
    msgs = create.call_args.kwargs["messages"]
    assert msgs == [{"role": "system", "content": "SYSTEM PROMPT"}, {"role": "user", "content": "What is FEAT?"}]
