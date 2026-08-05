"""The checks that keep v2 and v3 honest, and the judge specification's own contract."""

import json
from pathlib import Path

import pytest

from my_env2.adapter import ChatAdapter
from my_env2.llm import AuthoringError
from my_env2.prompts import _complaints, _forbidden, _merge_judge, _text
from my_env2.seed import DraftChat, DraftMessage, DraftUser, WorldDraft, build

SPEC = json.loads(
    (Path(__file__).parents[1] / "my_env2" / "action_spec.json").read_text()
)

ADAPTER = ChatAdapter()

SEED, BINDING = build(
    WorldDraft(
        actor_name="You",
        users=[
            DraftUser(ref="u1", name="Bo", handle="bob"),
            DraftUser(ref="u2", name="Bobby", handle="bobby"),
        ],
        chats=[
            DraftChat(ref="c1", name="launch", members=["u1", "u2"], symbol="$chat_0")
        ],
        messages=[
            DraftMessage(
                ref="m1",
                chat="c1",
                sender="u1",
                text="hello there",
                order=1,
                symbol="$message_0",
            )
        ],
    ),
    {"$chat_0": "chat", "$message_0": "message"},
)

# One described entity: the message. Its author is not described, so naming Bo is allowed.
REFERENCES = {
    "$message_0": {
        "mode": "message_by_text",
        "params": {"text": "hello there"},
        "phrase": "the message about hello there",
        "predicate": "the one message whose text contains hello there",
    }
}


def forbidden(references=None):
    return _forbidden(
        SPEC, ADAPTER, SEED, BINDING, REFERENCES if references is None else references
    )


def test_forbidden_covers_ids_and_the_names_of_actions():
    """An id hands the agent the resolution step; a tool name hands it the call."""
    assert {"u_bob", "u_bobby", "c_001", "m_001"} <= forbidden()
    assert {"mark_read", "chat_mark_read", "ask_question"} <= forbidden()


def test_a_leak_is_matched_on_a_word_boundary():
    """User ids are derived from handles and so overlap as prefixes. A substring match reports
    `u_bob` leaked every time `u_bobby` appears, and the count stops meaning anything."""
    assert _complaints("Ping u_bobby about the rollout.", forbidden()) == [
        "named 'u_bobby'"
    ]
    assert _complaints("Ping the person who raised it.", forbidden()) == []


def test_naming_a_described_entity_outright_is_a_complaint():
    """A description with the answer bolted on — "Alice Rivera (whoever wrote about the freeze)" —
    hands back the very step the description existed to create."""
    chat = {
        "mode": "chat_containing_text",
        "params": {"text": "hello there"},
        "phrase": "the conversation where hello there came up",
        "predicate": "...",
    }
    described = forbidden({"$chat_0": chat})
    assert "launch" in described
    assert _complaints("Post it in the launch channel.", described) == [
        "named 'launch'"
    ]


def test_the_reference_itself_is_exempt():
    """Where the chosen mode IS the name, the name is the description and has to survive."""
    by_name = {
        "$chat_0": {
            "mode": "chat_by_name",
            "params": {"name": "launch"},
            "phrase": "the launch channel",
            "predicate": "...",
        }
    }
    assert "launch" not in forbidden(by_name)


def test_a_person_nobody_describes_may_be_named():
    """Only entities the prompt is supposed to work for are protected. Naming someone the task
    never refers to indirectly is ordinary world detail."""
    assert "Bo" not in forbidden()
    assert "bob" not in forbidden()


def test_naming_a_tool_is_a_complaint():
    assert _complaints("Use ask_question on the repo.", forbidden()) == [
        "named 'ask_question'"
    ]


@pytest.mark.parametrize(
    "prompt",
    ["1. Do the thing\n2. Do the other", "- Do the thing\n- Do the other"],
)
def test_enumeration_is_a_complaint(prompt):
    assert any("enumerates" in c for c in _complaints(prompt, set()))


def test_prose_is_not_flagged_as_enumeration():
    prose = (
        "Could you find out what the build system is and let the launch channel know?"
    )
    assert _complaints(prose, set()) == []


ITEM = {
    "id": "carry:c0a1:text",
    "step": 2,
    "requirement": "the text of step 2 must carry what step 1 returned",
    "delivered_in": "the message step 2 posts",
    "sources": [],
}


def test_a_judge_item_needs_an_answer_not_a_restatement_of_the_question():
    """`expected` is what a grader compares against. Without it the item is inert, so the stage
    is failed rather than shipped with a hole in its own scoring."""
    for authored in (
        [],
        [{"id": "carry:c0a1:text"}],
        [{"id": "other", "expected": "x"}],
    ):
        with pytest.raises(AuthoringError, match="no expected answer"):
            _merge_judge([ITEM], authored)


def test_a_judge_item_falls_back_to_the_derived_delivery_target():
    """Where the answer goes is decided from the plan, never left to the author — an author free
    to choose invents a message the plan does not contain."""
    merged = _merge_judge([ITEM], [{"id": ITEM["id"], "expected": "Bazel"}])
    assert merged == [
        {
            "id": ITEM["id"],
            "requirement": ITEM["requirement"],
            "expected": "Bazel",
            "hint": ITEM["delivered_in"],
            "delivered_in": ITEM["delivered_in"],
        }
    ]


def test_a_reply_with_no_prompt_is_refused():
    for reply in ({}, {"prompt": ""}, {"prompt": None}, {"prompt": 7}):
        with pytest.raises(AuthoringError, match="no .prompt. string"):
            _text(reply)
