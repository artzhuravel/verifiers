"""Concurrent dependency chains over a shared clock.

`gen_dependency_chain` (generate.py) builds ONE chain in isolation. This module builds N of
them simultaneously, turn by turn, from a shared pool of everything produced so far. Because
the pool is global, a chain may consume what another chain produced — and because a chain can
skip a turn, it can wait for an entity that does not exist yet. That waiting is the point: it
is what lets one strand of a task genuinely depend on another.

Once links cross, the result is one DAG and a "chain" is a *thread*: bookkeeping that controls
one strand's depth, its skip rate and its share of distractors, not a topologically separate
object.

Two things differ from the single-chain generator on purpose:

- **Chains terminate, they do not raise.** A chain that runs out of feasible actions stops
  where it is rather than failing the batch, so no feasibility look-ahead is needed.
- **Sinks are unrestricted.** A chain can continue past an action that produces nothing, since
  its next link may consume some other chain's output.

References between actions are by **key**, not by position: an edge names the action it draws
from (`{"source": "c0a1", ...}`), so the timeline survives having distractors interleaved into
it later. Relative offsets would silently shift.

This module deliberately says nothing about the expected state diff — it advances `sim` only so
that created ids are real and feasibility is exact.
"""

from dataclasses import dataclass, field
from random import Random
from typing import Any

from my_env.generate import EnvAdapter, _Action, _consumer_index, _offer, _parse


@dataclass
class ChainConfig:
    """How one thread behaves. Every field is per-thread, so threads can differ."""

    max_depth: int = 3
    """How many dependent links this thread aims for. It stops early — without failing — if no
    feasible action is available, rather than breaking the whole batch."""
    max_breadth: int = 1
    """Cap on how many earlier outputs a SINGLE action may consume. Sampled per action once a
    feasible one is chosen, then clamped by how many compatible outputs actually exist, and
    again by the slot's `arity` (a slot declared `one` always takes exactly one)."""
    p_skip: float = 0.0
    """Chance this thread stays silent for a whole turn. Silence is what lets it wait for
    another thread to produce something it can use."""
    p_cross: float = 0.3
    """Chance this action may borrow from OUTSIDE its own thread. At 0.0 the thread only ever
    consumes what it produced itself, so it reads as one self-contained errand; at 1.0 the
    whole pool is fair game and — since most of the pool belongs to other threads — it mostly
    consumes their work. Rolled per action, and never overridden: a thread that finds nothing
    it is allowed to consume stops early rather than reaching outside anyway."""
    p_unrelated: float = 0.0
    """Chance of also emitting an action that depends on nothing — a distractor sub-task. It
    does not count toward depth, and it is not a link in the dependency chain."""


@dataclass
class _Produced:
    """One earlier action that later ones can draw from."""

    key: str
    chain: int
    turn: int
    offer: tuple[str, str]
    entity_id: str | None


@dataclass
class _Thread:
    config: ChainConfig
    turns: list[list[dict]] = field(default_factory=list)
    depth: int = 0
    active: bool = True
    emitted: int = 0  # only for minting keys


def gen_dependency_chains(
    spec: dict,
    adapter: EnvAdapter,
    sim: Any,
    rng: Random,
    configs: list[ChainConfig],
    *,
    max_global_depth: int | None = None,
    max_turns: int = 200,
) -> list[list[list[dict]]]:
    """Generate `len(configs)` interleaved dependency chains.

    Returns one timeline per thread, aligned on a shared clock: `result[i][t]` is the list of
    actions thread `i` performed at turn `t` — empty when it skipped or had already finished.
    Every timeline has the same number of turns, so `t` means the same thing across threads.

    Generation stops when every thread is finished, or as soon as any thread reaches
    `max_global_depth`. That cap is **off** unless asked for: setting it halts the whole batch
    the moment one thread gets there, which truncates every slower thread — with any skipping
    at all, the threads that lose depth are systematically the ones that skipped. Leave it
    unset and each thread runs to its own `max_depth`. `max_turns` is a backstop against a
    pathological run of skips, not a tuning knob; note that a high `p_skip` stretches the
    timeline, since turn count is what absorbs the waiting.
    """
    if not configs:
        raise ValueError("need at least one chain config")
    if any(config.max_depth < 1 for config in configs):
        raise ValueError("every chain needs max_depth >= 1")
    if any(config.max_breadth < 1 for config in configs):
        raise ValueError("every chain needs max_breadth >= 1")

    actions = _parse(spec, [entry["id"] for entry in spec["actions"]])
    consumers = _consumer_index(actions)
    producers = [action for action in actions if action.produces]
    by_id = {action.id: action for action in actions}
    object_types = {action.object_type for action in actions if action.object_type}

    threads = [_Thread(config=config) for config in configs]
    pool: list[_Produced] = []  # everything produced in STRICTLY earlier turns
    # Entities that existed when the current turn began. An arg the generator samples freely
    # must come from here rather than from live `sim`: `sim` already holds whatever earlier
    # threads created THIS turn, and drawing from that would make an action silently depend on
    # a same-turn sibling — a dependency `depends_on` does not record and the turn's stated
    # independence denies.
    frozen: dict[str, list[str]] = {}

    def usable(action: _Action) -> bool:
        return action.object_type is None or bool(frozen.get(action.object_type))

    def perform(action: _Action, thread_index: int, turn: int, sources: list[_Produced],
                consume: dict | None, *, unrelated: bool = False) -> dict:
        """Apply one action and build its record. `sources` is empty for a root/distractor."""
        thread = threads[thread_index]
        key = f"c{thread_index}a{thread.emitted}"
        thread.emitted += 1
        if action.open_ended:
            # A placeholder slot, exactly as in `generate`: no API call, no state effect.
            objects, args, entity_id, value = {}, {}, None, None
        else:
            if consume is not None and consume["slot"] == "object":
                if len(sources) > 1:
                    # Unreachable in this spec: create_chat.member_ids is the only object slot
                    # with arity `many`, and nothing produces a user.
                    raise NotImplementedError(
                        f"list-valued object binding for {action.id}.{consume['param']}"
                    )
                object_id = sources[0].entity_id
            elif action.object_type:
                object_id = rng.choice(frozen[action.object_type])
            else:
                object_id = None
            outcome = adapter.apply(action.id, object_id, sim, rng)
            # A link must succeed — a failed action produces nothing to chain from. Invalid
            # actions are the outer task generator's business, not a chain's.
            assert not outcome.error, (action.id, object_id, outcome)
            objects = {p: outcome.args[p] for p in action.ref_params if p in outcome.args}
            args, entity_id, value = outcome.args, outcome.entity_id, outcome.value
        return {
            "key": key,
            "chain": thread_index,
            "turn": turn,
            "action": action.id,
            "tool": action.tool,
            "kind": action.kind,
            "open_ended": action.open_ended,
            "objects": objects,
            "args": args,
            "expect_error": False,
            "entity_id": entity_id,
            # By key, not by offset: an interleaved distractor must not be able to shift what
            # an edge points at.
            "depends_on": [
                {
                    "source": source.key,
                    "via": consume["slot"],
                    "param": consume["param"],
                    "entity_id": source.entity_id,
                }
                for source in sources
            ],
            "produced_value": value,
            "unrelated": unrelated,
        }

    def root(thread_index: int, turn: int) -> dict | None:
        """Open a thread's own strand: an action that produces, depending on nothing."""
        candidates = [action for action in producers if usable(action)]
        if not candidates:
            return None
        return perform(rng.choice(candidates), thread_index, turn, [], None)

    def consume(thread_index: int, turn: int, eligible: list[_Produced]) -> dict | None:
        """One link drawing on `eligible`, or None if nothing there can be consumed."""
        if not eligible:
            return None
        config = threads[thread_index].config
        # Group by offer type, so a fan-in draws several sources of one type into one slot.
        available: dict[tuple[str, str], list[_Produced]] = {}
        for produced in eligible:
            available.setdefault(produced.offer, []).append(produced)
        options = [
            (offer, action, consume_slot)
            for offer, group in available.items()
            for action, consume_slot in consumers.get(offer, [])
            if usable(action)
            # An object slot binds a real id; an info producer has none to give.
            and (consume_slot["slot"] != "object" or any(p.entity_id for p in group))
        ]
        if not options:
            return None
        offer, action, consume_slot = rng.choice(options)
        group = available[offer]
        if consume_slot["slot"] == "object":
            group = [produced for produced in group if produced.entity_id]
        # Breadth is sampled only once an action is settled on, then clamped twice: by what
        # exists, and by whether the slot can hold more than one thing at all.
        width = 1 if consume_slot["arity"] == "one" else rng.randint(1, config.max_breadth)
        width = min(width, len(group))
        return perform(action, thread_index, turn, rng.sample(group, width), consume_slot)

    def dependent(thread_index: int, turn: int) -> dict | None:
        """The thread's next link, honouring how far outside itself it is willing to look."""
        thread = threads[thread_index]
        own = [produced for produced in pool if produced.chain == thread_index]
        other = [produced for produced in pool if produced.chain != thread_index]
        borrow = rng.random() < thread.config.p_cross

        if thread.depth == 0:
            # Nothing emitted yet. Borrowing means picking up another thread's work — which is
            # what makes a skipped turn meaningful, since the thread can wait for output that
            # does not exist yet. Otherwise it opens an errand of its own.
            if borrow and other:
                return consume(thread_index, turn, other) or root(thread_index, turn)
            return root(thread_index, turn)

        # Already started, so extend the strand rather than restart it: only a thread's FIRST
        # action may depend on nothing, or `depth` would count roots as chain depth. A thread
        # whose own links were all sinks has nothing of its own left to build on, and unless it
        # is willing to borrow it stops here.
        return consume(thread_index, turn, own + other if borrow else own)

    def distractor(thread_index: int, turn: int) -> dict | None:
        """An action deliberately depending on nothing — a sub-task that goes nowhere."""
        candidates = [action for action in actions if usable(action)]
        if not candidates:
            return None
        return perform(rng.choice(candidates), thread_index, turn, [], None, unrelated=True)

    turn = 0
    while any(thread.active for thread in threads) and turn < max_turns:
        frozen = {etype: list(adapter.objects_of_type(sim, etype)) for etype in object_types}
        produced_this_turn: list[_Produced] = []
        for index, thread in enumerate(threads):
            emitted: list[dict] = []
            if thread.active and rng.random() >= thread.config.p_skip:
                step = dependent(index, turn)
                if step is None:
                    thread.active = False  # out of feasible actions: stop, do not fail
                else:
                    emitted.append(step)
                    thread.depth += 1
                    if thread.depth >= thread.config.max_depth:
                        thread.active = False
                    if rng.random() < thread.config.p_unrelated:
                        if extra := distractor(index, turn):
                            emitted.append(extra)
            thread.turns.append(emitted)
            for step in emitted:
                if by_id[step["action"]].produces:
                    produced_this_turn.append(
                        _Produced(
                            step["key"],
                            index,
                            turn,
                            _offer(by_id[step["action"]]),
                            step["entity_id"],
                        )
                    )
        # Only now do this turn's outputs become consumable, so nothing depends on an action in
        # its own turn and thread order within a turn carries no meaning.
        pool.extend(produced_this_turn)
        turn += 1
        if max_global_depth is not None and any(
            thread.depth >= max_global_depth for thread in threads
        ):
            break

    return [thread.turns for thread in threads]
