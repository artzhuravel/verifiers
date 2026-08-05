"""Stage 1 contracts, checked over many seeds rather than one lucky sample."""

import json
import random
from collections import Counter
from pathlib import Path

from my_env2.spec import parse_actions
from my_env2.symbolic import ChainConfig, generate_sequence

SPEC = json.loads(
    (Path(__file__).parents[1] / "my_env2" / "action_spec.json").read_text()
)
ACTIONS = {action.id: action for action in parse_actions(SPEC)}

CONFIGS = [
    ChainConfig(max_depth=3, max_breadth=2, p_cross=0.4),
    ChainConfig(max_depth=3, max_breadth=2, p_skip=0.3, p_cross=0.5, p_unrelated=0.2),
    ChainConfig(max_depth=2, max_breadth=1, p_cross=0.2),
]


def sequences(n: int = 120):
    return [
        generate_sequence(SPEC, random.Random(idx), CONFIGS, task_id=f"t{idx}")
        for idx in range(n)
    ]


def test_nothing_concrete_escapes():
    """The whole point of Stage 1: no id that could belong to a real environment."""
    for sequence in sequences():
        for step in sequence.steps:
            for value in step.refs.values():
                for symbol in value if isinstance(value, list) else [value]:
                    assert symbol.startswith("$"), (step.key, symbol)
            for symbol in step.content.values():
                assert symbol.startswith("$"), (step.key, symbol)
            for symbol in (step.produces_entity, step.produces_value):
                assert symbol is None or symbol.startswith("$")


def test_manifest_covers_every_symbol():
    for sequence in sequences():
        declared = {entry.symbol for entry in sequence.manifest}
        for step in sequence.steps:
            for value in step.refs.values():
                for symbol in value if isinstance(value, list) else [value]:
                    assert symbol in declared, (sequence.task_id, step.key, symbol)
            if step.produces_entity:
                assert step.produces_entity in declared
        # And nothing declared is unused: an entity nobody touches would be authored for
        # nothing.
        used = {
            symbol
            for step in sequence.steps
            for value in step.refs.values()
            for symbol in (value if isinstance(value, list) else [value])
        } | {step.produces_entity for step in sequence.steps if step.produces_entity}
        assert declared == used, declared ^ used


def test_origin_matches_who_creates_it():
    for sequence in sequences():
        created = {
            step.produces_entity for step in sequence.steps if step.produces_entity
        }
        for entry in sequence.manifest:
            if entry.origin == "rollout":
                assert entry.symbol in created
                assert entry.created_by is not None
            else:
                assert entry.symbol not in created
                assert entry.created_by is None


def test_edges_point_strictly_backwards():
    """Turn-major linearisation is only a valid order because of this."""
    for sequence in sequences():
        by_key = {step.key: step for step in sequence.steps}
        for step in sequence.steps:
            for edge in step.depends_on:
                assert by_key[edge["source"]].turn < step.turn, (step.key, edge)
            for sources in step.carries.values():
                for key in sources:
                    assert by_key[key].turn < step.turn


def test_object_edges_carry_an_entity_and_value_edges_do_not():
    for sequence in sequences():
        by_key = {step.key: step for step in sequence.steps}
        for step in sequence.steps:
            for edge in step.depends_on:
                source = by_key[edge["source"]]
                if edge["via"] == "object":
                    assert source.produces_entity == edge["symbol"]
                    assert edge["symbol"] is not None
                else:
                    assert source.produces_value is not None


def test_no_write_is_performed_twice_on_one_entity():
    """A second `add_reaction` or `mark_read` on the same entity writes a fact that is
    already true, which the reward cannot tell from doing nothing."""
    guarded = {
        action_id for action_id, action in ACTIONS.items() if action.meaningful_when
    }
    assert guarded, (
        "the spec no longer declares meaningful_when; this guard is now vacuous"
    )
    for sequence in sequences():
        pairs = Counter()
        for step in sequence.steps:
            if step.action in guarded:
                for value in step.refs.values():
                    for symbol in value if isinstance(value, list) else [value]:
                        pairs[(step.action, symbol)] += 1
        assert not [pair for pair, count in pairs.items() if count > 1], pairs


def test_history_dependent_actions_never_touch_a_rollout_entity():
    """`mark_read` on a chat the agent just created marks nothing."""
    for sequence in sequences():
        origin = {entry.symbol: entry.origin for entry in sequence.manifest}
        for step in sequence.steps:
            for requirement in ACTIONS[step.action].meaningful_when:
                if not requirement.get("requires_history"):
                    continue
                for symbol in [step.refs[requirement["ref"]]]:
                    assert origin[symbol] == "seed", (step.key, step.action, symbol)


def test_slots_line_up_with_the_steps():
    for sequence in sequences():
        by_key = {step.key: step for step in sequence.steps}
        for slot in sequence.slots:
            step = by_key[slot.key]
            if slot.kind == "content":
                assert slot.param in step.content
                assert slot.param not in step.carries
            else:
                assert step.carries[slot.param] == slot.sources
                assert slot.param not in step.content


def test_every_content_param_is_either_authored_or_carried():
    for sequence in sequences():
        for step in sequence.steps:
            required = {
                param["name"]
                for param in ACTIONS[step.action].content_params()
                if param.get("required")
            }
            filled = set(step.content) | set(step.carries)
            assert required <= filled, (step.key, step.action, required - filled)


def test_shape_is_measured_not_configured():
    for sequence in sequences(40):
        shape = sequence.shape
        assert shape["steps"] == len(sequence.steps)
        assert shape["links_per_thread"] == [
            sum(1 for step in sequence.steps if step.chain == i and not step.unrelated)
            for i in range(len(CONFIGS))
        ]
        assert shape["object_edges"] + shape["value_edges"] == sum(
            len(step.depends_on) for step in sequence.steps
        )


def test_longest_chain_is_a_path_not_a_link_count():
    """A thread's links can all hang off one foreign source, which is a fan-out two deep however
    many links it has. Reporting link count as depth would make every difficulty regression on
    this field a regression on something else."""
    diverged = 0
    for sequence in sequences(60):
        by_key = {step.key: step for step in sequence.steps}

        # Independently: the longest path, walked backwards from each step.
        def depth_of(key, by_key=by_key):
            edges = by_key[key].depends_on
            return 1 + max((depth_of(edge["source"]) for edge in edges), default=0)

        longest = max((depth_of(step.key) for step in sequence.steps), default=0)
        assert sequence.shape["longest_chain"] == longest
        assert longest <= sequence.shape["steps"]
        if (
            sequence.shape["links_per_thread"]
            != sequence.shape["longest_chain_per_thread"]
        ):
            diverged += 1
    assert diverged > 10, diverged


def test_reuse_actually_happens():
    """Without reuse every step invents its own world, and no prompt can ever say
    "that chat" — so this is a property worth pinning down, not an accident."""
    shared = 0
    for sequence in sequences():
        for entry in sequence.manifest:
            if (
                entry.origin == "seed"
                and len({role["step"] for role in entry.roles}) > 1
            ):
                shared += 1
    assert shared > 20, shared
