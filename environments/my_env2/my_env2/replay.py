"""Stage 6 — binding every placeholder and replaying the sequence against the built seed.

The stateful generator got `expected` for free: the world it walked through *was* the end
state. Nothing here is free. The seed now exists for the first time, so this is where symbols
become ids and where the plan is executed for real, once, to find out what a faithful run
leaves behind.

It is also the pipeline's validity gate. Every earlier stage is a proposal — the sequence
proposes a shape, the authoring stages propose a world — and this is the first point at which
the two are made to meet. A step that errors means the proposals do not fit, and the task is
discarded rather than patched: a repaired task is one whose prompt describes something other
than what was built.

Free text stays unresolved here. Replay writes the placeholder itself into every message body,
because `signature` excludes content — so Stage 7 can decide what those messages actually say
afterwards without invalidating a single fact in `expected`.
"""

from dataclasses import dataclass, field

from my_env2.adapter import ChatAdapter
from my_env2.spec import parse_actions
from my_env2.state import ChatState
from my_env2.symbolic import Sequence


class ReplayError(RuntimeError):
    """The sequence cannot be executed against this seed, so the task is malformed."""


@dataclass
class Replay:
    expected: ChatState
    binding: dict[str, str]
    """Every symbol, seed and rollout alike, mapped to a real entity id."""
    observed: dict[str, str] = field(default_factory=dict)
    """Step key -> what that step returned, for the reads where there is something to name.
    This is the ground truth behind a carry requirement: the information a later message has
    to contain is whatever the read it depends on actually produced."""
    args: dict[str, dict] = field(default_factory=dict)
    """Step key -> the concrete args replay used, so a prompt can be checked against them."""
    step_deltas: dict[str, list[str]] = field(default_factory=dict)
    """Step key -> the facts that step added, measured one step at a time."""
    turn_diffs: list[dict] = field(default_factory=list)
    """Per turn: the facts that turn added. Recorded because they make a failed rollout
    debuggable — they say which turn a run stopped matching at."""
    no_ops: list[str] = field(default_factory=list)
    """Write steps that changed nothing the reward can see.

    The previous pipeline could only estimate this; here the world was authored expressly to
    make each step meaningful, so a no-op is a measured failure of that authoring and the task
    is dropped. Measured, not predicted: a predicate over args would have to reimplement each
    tool's effect logic in a second place, and the two would drift."""
    barren: list[str] = field(default_factory=list)
    """Reads that came back empty.

    The read counterpart of a no-op, and it matters for the same reason. A read of a chat with no
    history returns `[]`; the manifest asked for history and the authoring stage did not deliver
    it. Nothing errors, the state diff has nothing to say about a read either way, and the
    judge item built from it would demand information that does not exist."""


def replay(
    spec: dict,
    sequence: Sequence,
    adapter: ChatAdapter,
    seed: ChatState,
    binding: dict[str, str],
) -> Replay:
    """Execute the whole sequence against a copy of `seed`.

    `binding` covers the seed entities (from `seed.build`); rollout entities are bound here as
    the steps that create them run.
    """
    actions = {action.id: action for action in parse_actions(spec)}
    state = seed.model_copy(deep=True)
    bound = dict(binding)
    result = Replay(expected=state, binding=bound)

    facts: set = adapter.signature(state, seed)
    for step in sequence.steps:
        action = actions[step.action]
        if action.external:
            # No state effect and no observable answer: an external read is authored, not run.
            continue

        args = {}
        for param, value in step.refs.items():
            if isinstance(value, list):
                args[param] = [_lookup(bound, symbol, step.key) for symbol in value]
            else:
                args[param] = _lookup(bound, value, step.key)
        # The placeholder itself goes in as the value. It is deliberately visible: if one ever
        # leaked into a shipped task, `<text_0>` in a message body is unmistakable.
        for param, symbol in step.content.items():
            args[param] = symbol
        for param in step.carries:
            args[param] = f"$carried_{step.key}_{param}"

        outcome = adapter.execute(action.id, args, state)
        if adapter.is_error(outcome):
            raise ReplayError(
                f"step {sequence.number(step.key)} ({action.id}) failed: {outcome}"
            )
        result.args[step.key] = args

        created = adapter.created(action.id, args, outcome)
        if step.produces_entity:
            if not created:
                raise ReplayError(
                    f"step {sequence.number(step.key)} ({action.id}) was expected to create "
                    f"{step.produces_entity} but returned no id"
                )
            if step.produces_entity in bound:
                raise ReplayError(f"{step.produces_entity} was already bound")
            bound[step.produces_entity] = created
        if (value := adapter.observed(action.id, outcome)) is not None:
            result.observed[step.key] = value
            if value.strip() in ("", "[]", "{}", "null"):
                result.barren.append(step.key)

        after = adapter.signature(state, seed)
        result.step_deltas[step.key] = sorted(map(str, after - facts))
        if action.kind == "write" and after == facts:
            result.no_ops.append(step.key)
        facts = after

    for turn in range(len(sequence.timelines[0]) if sequence.timelines else 0):
        added = [
            fact
            for step in sequence.steps
            if step.turn == turn
            for fact in result.step_deltas.get(step.key, [])
        ]
        result.turn_diffs.append({"turn": turn, "added": sorted(added)})

    unbound = sorted(
        entry.symbol for entry in sequence.manifest if entry.symbol not in bound
    )
    if unbound:
        raise ReplayError(f"replay left {', '.join(unbound)} unbound")
    return result


def _lookup(binding: dict[str, str], symbol: str, key: str) -> str:
    if symbol not in binding:
        raise ReplayError(f"step {key} refers to {symbol}, which nothing bound")
    return binding[symbol]


def expected_facts(
    adapter: ChatAdapter, seed: ChatState, expected: ChatState
) -> list[str]:
    """What the deterministic reward will look for, as readable lines."""
    delta = adapter.signature(expected, seed) - adapter.signature(seed, seed)
    return sorted(map(str, delta))
