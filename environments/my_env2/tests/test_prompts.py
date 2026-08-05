"""The checks that keep v2 and v3 honest, and the judge specification's own contract."""

import json
from pathlib import Path

import pytest

from my_env2.adapter import ChatAdapter
from my_env2.llm import AuthoringError
from my_env2.prompts import (
    _complaints,
    _forbidden,
    _merge_judge,
    _rewrite_judge,
    _text,
    stale_references,
)
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


# --- a description introduces a thing once ------------------------------------------------

PHRASE = "the one conversation you still have not caught up on"


def test_a_description_pasted_twice_is_a_complaint():
    """The defect this check exists for: 40 of 81 phrase uses over twelve tasks were the same
    description pasted again, because the stage asked for per-occurrence substitution."""
    twice = f"Catch up on {PHRASE} and then post a summary to {PHRASE}."
    assert any("pasted the description" in c for c in _complaints(twice, set(), [PHRASE]))


def test_a_description_used_once_and_referred_back_to_is_clean():
    once = f"Catch up on {PHRASE}, summarise what you find, and post it back there."
    assert [c for c in _complaints(once, set(), [PHRASE]) if "pasted" in c] == []


def test_sequencing_is_only_flagged_where_the_rung_forbids_it():
    """v2 is prose and may read sequentially; v3 and v4 forbid "and then" chaining."""
    chained = "Read the room; then post a summary."
    assert [c for c in _complaints(chained, set()) if "sequencing" in c] == []
    assert any(
        "sequencing" in c for c in _complaints(chained, set(), flag_sequencing=True)
    )


# --- the judge specification travels with the prompt --------------------------------------

MERGED = {
    "id": "carry:c0a1:text",
    "requirement": "the text of step 2 must carry what step 1 returned",
    "expected": "names Bazel as the build system",
    "hint": "the message the agent sent to chat c_001 in step 2",
    "delivered_in": "the message step 2 posts",
}


def test_a_rung_that_leaves_an_item_unrestated_is_refused():
    """An item still naming a step or an id describes a task the higher rung never gave."""
    for authored in ([], [{"id": MERGED["id"]}], [{"id": "other", "expected": "x"}]):
        with pytest.raises(AuthoringError, match="was not restated"):
            _rewrite_judge([MERGED], authored)


def test_restating_keeps_the_requirement_and_the_delivery_target():
    """Only `expected` and `hint` are the author's. Letting it restate the requirement invites a
    weaker one; letting it choose the destination invents a message the plan does not contain."""
    [restated] = _rewrite_judge(
        [MERGED],
        [{"id": MERGED["id"], "expected": "says the build system is Bazel",
          "hint": "the summary posted back to that channel"}],
    )
    assert restated["expected"] == "says the build system is Bazel"
    assert restated["hint"] == "the summary posted back to that channel"
    assert restated["requirement"] == MERGED["requirement"]
    assert restated["delivered_in"] == MERGED["delivered_in"]


def test_a_hint_left_out_falls_back_rather_than_going_empty():
    [restated] = _rewrite_judge([MERGED], [{"id": MERGED["id"], "expected": "Bazel"}])
    assert restated["hint"] == MERGED["hint"]


# --- a description the task's own work makes false -----------------------------------------


def test_a_reference_the_work_invalidates_is_detected():
    """Uniqueness is proved against the seed, but `chat_only_with_unread` stops holding the moment
    the task marks that chat read — and the prompt then goes on using the phrase."""
    unread_seed, unread_binding = build(
        WorldDraft(
            actor_name="You",
            users=[DraftUser(ref="u1", name="Bo", handle="bob")],
            chats=[DraftChat(ref="c1", name="infra", members=["u1"], symbol="$chat_0")],
            messages=[
                DraftMessage(ref="m1", chat="c1", sender="u1", text="anyone around?",
                             order=1, read_by_actor=False)
            ],
        ),
        {"$chat_0": "chat"},
    )
    reference = {
        "$chat_0": {"mode": "chat_only_with_unread", "params": {},
                    "phrase": "the one conversation you still have not caught up on",
                    "predicate": "..."}
    }
    assert stale_references(ADAPTER, unread_seed, unread_binding, reference) == set()

    caught_up = unread_seed.model_copy(deep=True)
    for message in caught_up.messages:
        message.read_by = [*message.read_by, caught_up.me]
    assert stale_references(ADAPTER, caught_up, unread_binding, reference) == {"$chat_0"}
