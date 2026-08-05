"""Everything between Stage 1 and Stage 6 that does not need a model.

The authoring stages are replaced by `stub_world`, so what is under test here is the spine:
does a built world satisfy the sequence, does every reference provably resolve, does replay bind
every symbol, and does `expected` reflect the whole timeline rather than a truncated one.
"""

import json
import random
from pathlib import Path

import pytest

from my_env2.adapter import ChatAdapter
from my_env2.prompts import judge_items
from my_env2.replay import replay
from my_env2.seed import ME, build
from my_env2.spec import parse_actions, reference_modes
from my_env2.symbolic import ChainConfig, generate_sequence
from tests.stub import stub_world

SPEC = json.loads(
    (Path(__file__).parents[1] / "my_env2" / "action_spec.json").read_text()
)
ACTIONS = {action.id: action for action in parse_actions(SPEC)}
ADAPTER = ChatAdapter()

CONFIGS = [
    ChainConfig(max_depth=3, max_breadth=2, p_cross=0.4),
    ChainConfig(max_depth=2, max_breadth=2, p_skip=0.3, p_cross=0.5, p_unrelated=0.2),
]


def built(idx: int):
    sequence = generate_sequence(SPEC, random.Random(idx), CONFIGS, task_id=f"t{idx}")
    required = {
        entry.symbol: entry.entity_type
        for entry in sequence.manifest
        if entry.origin == "seed"
    }
    seed, binding = build(stub_world(sequence), required)
    return sequence, seed, binding


CASES = [built(idx) for idx in range(60)]


def test_the_world_satisfies_the_sequence():
    for sequence, seed, binding in CASES:
        for entry in sequence.manifest:
            if entry.origin != "seed":
                continue
            entity_id = binding[entry.symbol]
            assert entity_id in ADAPTER.objects_of_type(seed, entry.entity_type)


def test_the_actor_can_see_everything():
    """`list_chats` shows only the actor's chats, so anything else is unreachable."""
    for _, seed, _ in CASES:
        assert seed.me == ME
        for chat in seed.chats.values():
            assert ME in chat.member_ids
        for message in seed.messages:
            assert message.sender_id in seed.chats[message.chat_id].member_ids


def test_the_actor_never_reacts_in_the_seed():
    """A seeded reaction by the actor makes a task's own add_reaction a no-op."""
    for _, seed, _ in CASES:
        for message in seed.messages:
            for reactors in message.reactions.values():
                assert ME not in reactors


def test_every_core_entity_gets_a_reference_that_resolves():
    """Not "some mode exists" but "the adapter can derive params that single it out" — Stage 9
    strips ids out of the prompt, so an entity without one leaves an unanswerable task."""
    modes = reference_modes(SPEC)
    for sequence, seed, binding in CASES:
        for entry in sequence.manifest:
            if entry.origin != "seed":
                continue
            target = binding[entry.symbol]
            working = [
                mode.id
                for mode in modes[entry.entity_type]
                if (params := ADAPTER.mode_params(seed, mode.id, target)) is not None
                and ADAPTER.resolve(seed, mode.id, params) == [target]
            ]
            assert working, (sequence.task_id, entry.symbol, entry.entity_type, target)


def test_declared_modes_and_implemented_modes_agree():
    for entity_type, modes in reference_modes(SPEC).items():
        for mode in modes:
            assert hasattr(ADAPTER, f"_mode_{mode.id}"), mode.id
            # And the params the spec declares are the ones the resolver takes.
            _, seed, _ = CASES[0]
            derived = ADAPTER.mode_params(
                seed, mode.id, next(iter(ADAPTER.objects_of_type(seed, entity_type)))
            )
            if derived is not None:
                assert set(derived) == {p["name"] for p in mode.params}, mode.id


def test_replay_binds_every_symbol_and_never_errors():
    for sequence, seed, binding in CASES:
        replayed = replay(SPEC, sequence, ADAPTER, seed, binding)
        assert set(replayed.binding) >= {entry.symbol for entry in sequence.manifest}
        for symbol, entity_id in replayed.binding.items():
            kind = sequence.entry(symbol).entity_type
            assert entity_id in ADAPTER.objects_of_type(replayed.expected, kind)


def test_replay_leaves_the_seed_alone():
    for sequence, seed, binding in CASES:
        before = seed.model_dump_json()
        replay(SPEC, sequence, ADAPTER, seed, binding)
        assert seed.model_dump_json() == before


def test_expected_covers_the_whole_timeline():
    """One fact per non-external step that writes anything. A truncated replay would show up as
    a missing turn rather than as an error, so it is worth pinning down explicitly."""
    for sequence, seed, binding in CASES:
        replayed = replay(SPEC, sequence, ADAPTER, seed, binding)
        writes = [
            step
            for step in sequence.steps
            if not ACTIONS[step.action].external and step.kind == "write"
        ]
        added = ADAPTER.signature(replayed.expected, seed) - ADAPTER.signature(
            seed, seed
        )
        assert len(added) >= len(writes), (sequence.task_id, len(added), len(writes))
        # Every step that creates an entity is bound to something that exists.
        for step in sequence.steps:
            if step.produces_entity:
                assert step.produces_entity in replayed.binding


def test_no_write_step_is_a_no_op():
    """The measured failure of the previous pipeline: 8.7% of its write links wrote a fact that
    was already true, which the reward cannot tell from doing nothing."""
    for sequence, seed, binding in CASES:
        state = seed.model_copy(deep=True)
        bound = dict(binding)
        previous = ADAPTER.signature(state, seed)
        for step in sequence.steps:
            action = ACTIONS[step.action]
            if action.external:
                continue
            args = {
                param: (
                    [bound[s] for s in value]
                    if isinstance(value, list)
                    else bound[value]
                )
                for param, value in step.refs.items()
            }
            args |= {param: symbol for param, symbol in step.content.items()}
            args |= {param: f"$carried_{param}" for param in step.carries}
            outcome = ADAPTER.execute(action.id, args, state)
            if step.produces_entity:
                bound[step.produces_entity] = ADAPTER.created(action.id, args, outcome)
            current = ADAPTER.signature(state, seed)
            if step.kind == "write":
                assert current != previous, (
                    f"{sequence.task_id} step {sequence.number(step.key)} "
                    f"({action.id}) changed nothing the reward can see"
                )
            previous = current


def test_no_read_comes_back_empty():
    """The read counterpart of a no-op write. A read of a chat with no history returns `[]`, and
    the judge item built from it would demand information that does not exist."""
    for sequence, seed, binding in CASES:
        replayed = replay(SPEC, sequence, ADAPTER, seed, binding)
        assert not replayed.barren, (
            sequence.task_id,
            [sequence.step(key).action for key in replayed.barren],
        )


def test_judge_items_cover_exactly_the_unverifiable_parts():
    for sequence, seed, binding in CASES:
        replayed = replay(SPEC, sequence, ADAPTER, seed, binding)
        items = judge_items(SPEC, sequence, replayed.observed)
        expected = {
            f"carry:{step.key}:{param}"
            for step in sequence.steps
            for param in step.carries
        }
        consumed = {
            source
            for step in sequence.steps
            for sources in step.carries.values()
            for source in sources
        }
        expected |= {
            f"report:{step.key}"
            for step in sequence.steps
            if step.produces_value and step.key not in consumed
        }
        assert {item["id"] for item in items} == expected


def test_every_step_reaches_at_least_one_reward_component():
    """A step neither reward can see is a step the prompt asks for and nothing grades. Writes go
    into `state_diff`; reads have to reach the judge, either by being carried into a message or by
    being reported back."""
    for sequence, seed, binding in CASES:
        replayed = replay(SPEC, sequence, ADAPTER, seed, binding)
        graded = {
            item["step"] for item in judge_items(SPEC, sequence, replayed.observed)
        }
        graded |= {
            source["step"]
            for item in judge_items(SPEC, sequence, replayed.observed)
            for source in item["sources"]
        }
        for number, step in enumerate(sequence.steps, 1):
            if step.kind == "write" and not ACTIONS[step.action].external:
                continue  # in the state diff by construction — no-ops are gated in replay
            assert number in graded, (sequence.task_id, number, step.action)


def test_internal_carry_items_know_the_real_answer():
    """A carry whose source is an internal read is checkable against what the read returned —
    which is the whole reason replay records observations."""
    grounded = 0
    for sequence, seed, binding in CASES:
        replayed = replay(SPEC, sequence, ADAPTER, seed, binding)
        for item in judge_items(SPEC, sequence, replayed.observed):
            for source in item["sources"]:
                step = sequence.steps[source["step"] - 1]
                if ACTIONS[step.action].external:
                    assert source["returned"] is None
                elif ACTIONS[step.action].produces:
                    assert source["returned"] is not None, item["id"]
                    grounded += 1
    assert grounded > 20, grounded


@pytest.mark.parametrize("idx", range(6))
def test_a_bad_draft_is_rejected_not_repaired(idx):
    from my_env2.seed import DraftError

    sequence = generate_sequence(SPEC, random.Random(idx), CONFIGS, task_id=f"t{idx}")
    required = {
        entry.symbol: entry.entity_type
        for entry in sequence.manifest
        if entry.origin == "seed"
    }
    draft = stub_world(sequence)
    # Drop one binding: the sequence now needs something the world does not contain.
    for entity in (*draft.users, *draft.chats, *draft.messages):
        if entity.symbol:
            entity.symbol = None
            break
    with pytest.raises(DraftError):
        build(draft, required)
