"""Environment-agnostic action-sequence generator (see ../DESIGN.md).

Reads an action spec and drives a deterministic random walk through an environment via
an adapter. Env specifics — state, tools, seeding, value args, id minting — live behind
the adapter; this module knows nothing about any particular environment.
"""

from dataclasses import dataclass
from functools import cache
from random import Random
from typing import Any, Protocol


@dataclass
class Outcome:
    """What `adapter.apply` reports back to the generic core."""

    error: bool
    entity_id: str | None
    """Id of the entity the action created or affected (for later judges/hooks)."""
    args: dict
    """The full args the adapter applied, including value args (for the prompt)."""
    value: str | None = None
    """The readable result of a *scalar internal* read (e.g. a user's handle) — a value the
    generator can show the authoring step so an obligation about it is grounded in something
    real. `None` for writes, for collections, and for external reads."""


class EnvAdapter(Protocol):
    def initial_state(self, rng: Random) -> Any: ...
    def objects_of_type(self, state: Any, entity_type: str) -> list[str]: ...
    def invalid_ref(self, entity_type: str) -> str: ...
    def apply(self, action: str, object_id: str | None, state: Any, rng: Random) -> Outcome: ...


_ENTITY_PRECONDS = ("entity_exists", "entities_exist")


@dataclass
class _Action:
    id: str
    tool: str
    kind: str  # "read" | "write"
    object_type: str | None  # entity type of the primary (enforced) object, for sampling
    enforced: bool  # the tool errors on a bad object ref -> invalidatable
    ref_params: list[str]  # every arg that references an entity, for reward matching
    open_ended: bool  # external/nondeterministic (e.g. DeepWiki) -> emitted as a slot
    produces: dict | None  # what the next link can consume; None = a sink
    consumes: list[dict]  # [{param, slot, type}] — how this action can be fed


def _parse(spec: dict, action_ids: list[str]) -> list[_Action]:
    by_id = {a["id"]: a for a in spec["actions"]}
    parsed = []
    for action_id in action_ids:
        entry = by_id[action_id]
        preconds = entry.get("preconditions", [])
        # The primary object drives sampling: the first single-entity precondition.
        primary = next((p for p in preconds if p.get("requires") == "entity_exists"), None)
        parsed.append(
            _Action(
                id=action_id,
                tool=entry["tool"],
                kind=entry["kind"],
                object_type=primary["entity"] if primary else None,
                enforced=bool(primary and primary.get("enforced")),
                ref_params=[p["ref"] for p in preconds if p.get("requires") in _ENTITY_PRECONDS],
                # External, nondeterministic actions (no controlled entity) become open slots.
                open_ended=any(p.get("requires") == "external_available" for p in preconds),
                produces=entry.get("produces"),
                consumes=entry.get("consumes", []),
            )
        )
    return parsed


_SLOT_KIND = {"object": "entity", "value": "info"}
"""Which produced kind a consumer slot accepts. An `object` slot takes an entity reference
(the id is bound, and `state_diff` then checks the placement); a `value` slot takes read
content (only the edge is recorded — the generator never invents the content)."""


def _offer(action: _Action) -> tuple[str, str] | None:
    """What a completed action offers the next link, as (kind, type). None for a sink."""
    if not action.produces:
        return None
    return action.produces["kind"], action.produces["type"]


def _consumer_index(actions: list[_Action]) -> dict[tuple[str, str], list[tuple[_Action, dict]]]:
    index: dict[tuple[str, str], list[tuple[_Action, dict]]] = {}
    for action in actions:
        for consume in action.consumes:
            key = (_SLOT_KIND[consume["slot"]], consume["type"])
            index.setdefault(key, []).append((action, consume))
    return index


def gen_dependency_chain(
    spec: dict,
    adapter: EnvAdapter,
    sim: Any,
    rng: Random,
    breadths: list[int],
) -> list[dict]:
    """Build a chain of dependent actions laid out in turns of the given widths.

    `breadths` is one width per turn: `[3, 1]` means three actions whose outputs all feed a
    single action in the next turn (three lookups, one message carrying all three), and
    `[1, 1, 1]` is a plain path. `sum(breadths)` actions are returned in order.

    Actions inside a turn are independent — they never consume each other. Every action in a
    turn beyond the first consumes a whole earlier turn: all of that turn's outputs, into one
    of its own slots. The first action of each turn is pinned to the turn immediately before
    it so the chain cannot break in the middle; the rest may reach further back, which is
    what keeps the shape space from collapsing (only `reply_to` both consumes and produces a
    message, so a strict path degenerates into a run of `reply_to`s).

    Advances `sim` in place, so the caller derives the expected state exactly as it does for
    an unchained plan — one simulation, one final state. `depends_on` holds one relative
    offset per source, so the steps survive being spliced into a larger timeline unchanged.

    Returns exactly `sum(breadths)` steps or raises. Two structural rules make that a
    guarantee rather than luck: sinks (actions that produce nothing) are confined to the
    final turn, and a turn wider than one must be homogeneous in output type so a single
    later slot with `arity: many` can absorb it. Chains carry no invalid steps — an errored
    action produces nothing, so it cannot be a link.
    """
    if len(breadths) < 2:
        raise ValueError(f"a chain needs at least two turns, got {list(breadths)}")
    if any(width < 1 for width in breadths):
        raise ValueError(f"every turn needs at least one action, got {list(breadths)}")

    actions = _parse(spec, [entry["id"] for entry in spec["actions"]])
    consumers = _consumer_index(actions)
    final_turn = len(breadths) - 1

    def usable(action: _Action) -> bool:
        # The action's own object precondition must be satisfiable in the current sim; a
        # bound object slot satisfies it by construction, so this only ever rules out an
        # action whose object still has to be sampled.
        return action.object_type is None or bool(adapter.objects_of_type(sim, action.object_type))

    def absorbers(offer, count: int, *, allow_sink: bool) -> list[tuple[_Action, dict]]:
        """Consumers that can take `count` outputs of one type into a single slot."""
        return [
            (action, consume)
            for action, consume in consumers.get(offer, [])
            if usable(action)
            and (allow_sink or action.produces)
            and (count == 1 or consume["arity"] == "many")
        ]

    @cache
    def viable(offer, turn: int) -> bool:
        """Can a turn `turn` whose whole layer offers `offer` be continued to the end?

        Recursive rather than one-step, because each turn's width constrains the *next*
        turn's type: `[1, 2, 1]` is only reachable through a middle layer of info producers
        (a chat, then two reads of it, then one message carrying both), and a one-step check
        would happily open with something that cannot get there.
        """
        if turn == final_turn:
            return True  # nothing has to consume the last turn
        return any(
            viable(_offer(action), turn + 1)
            for action, _ in absorbers(offer, breadths[turn], allow_sink=turn + 1 == final_turn)
        )

    if not any(
        viable(_offer(action), 0)
        for action in actions
        if action.produces and usable(action)
    ):
        raise ValueError(
            f"no chain can satisfy breadths={list(breadths)}: a turn wider than one needs a "
            "consumer with an `arity: many` slot of its output type"
        )

    steps: list[dict] = []
    # One entry per turn: the (position, action, produced id) of each action in it.
    per_turn: list[list[tuple[int, _Action, str | None]]] = []

    for turn, width in enumerate(breadths):
        # Decide the whole turn before applying any of it, so a stall raises before `sim`
        # has been advanced halfway through a layer.
        plan: list[tuple[int | None, dict | None, _Action]] = []
        for slot in range(width):
            if turn == 0:
                pool = [
                    (None, None, action)
                    for action in actions
                    if action.produces and usable(action) and viable(_offer(action), turn)
                ]
            else:
                # The first action of a turn must consume the previous turn, so the chain
                # stays connected; later ones may reach back for variety.
                sources = [turn - 1] if slot == 0 else list(range(turn))
                pool = [
                    (source, consume, action)
                    for source in sources
                    for action, consume in absorbers(
                        _offer(per_turn[source][0][1]),
                        len(per_turn[source]),
                        allow_sink=turn == final_turn,
                    )
                    if viable(_offer(action), turn)
                ]
            if plan and turn != final_turn:
                # Keep a non-final turn homogeneous, so the next turn can absorb it whole.
                want = _offer(plan[0][2])
                pool = [entry for entry in pool if _offer(entry[2]) == want]
            # Never take the same action on the same source twice inside a turn: the two
            # write identical facts, so the second is reward-equivalent to doing nothing.
            # Compared against every earlier pick in the turn, not just the last — the
            # duplicates are often not adjacent.
            taken = {(entry[0], entry[2].id) for entry in plan}
            if distinct := [entry for entry in pool if (entry[0], entry[2].id) not in taken]:
                pool = distinct
            if not pool:
                raise ValueError(
                    f"chain stalled at turn {turn + 1}/{len(breadths)} slot {slot + 1}/{width} "
                    f"(breadths={list(breadths)}, so far={[s['action'] for s in steps]})"
                )
            plan.append(rng.choice(pool))

        produced: list[tuple[int, _Action, str | None]] = []
        for source, consume, action in plan:
            position = len(steps)
            sources = per_turn[source] if source is not None else []
            if action.open_ended:
                # Same treatment as in `generate`: a placeholder slot, no state effect and
                # no API call here. Its value is unknown at generation time (external).
                objects, args, entity_id, value = {}, {}, None, None
            else:
                if consume is not None and consume["slot"] == "object":
                    if len(sources) > 1:
                        # Unreachable in this spec: the only `arity: many` object slot is
                        # create_chat.member_ids and no action produces a user. Raise rather
                        # than bind one id where a list belongs.
                        raise NotImplementedError(
                            f"list-valued object binding for {action.id}.{consume['param']}"
                        )
                    object_id = sources[0][2]  # the dependency: bind the produced id
                elif action.object_type:
                    object_id = rng.choice(adapter.objects_of_type(sim, action.object_type))
                else:
                    object_id = None
                outcome = adapter.apply(action.id, object_id, sim, rng)
                # A link must succeed; a failed action produces nothing to chain from.
                assert not outcome.error, (action.id, object_id, outcome)
                objects = {p: outcome.args[p] for p in action.ref_params if p in outcome.args}
                args, entity_id, value = outcome.args, outcome.entity_id, outcome.value

            steps.append(
                {
                    "action": action.id,
                    "tool": action.tool,
                    "kind": action.kind,
                    "open_ended": action.open_ended,
                    "objects": objects,
                    "args": args,
                    "expect_error": False,
                    "entity_id": entity_id,
                    # One edge per source, offsets relative: the chain does not know where
                    # it will be spliced, and relative offsets need no renumbering after.
                    "depends_on": [
                        {
                            "offset": source_position - position,
                            "via": consume["slot"],
                            "param": consume["param"],
                        }
                        for source_position, _, _ in sources
                    ],
                    "produced_value": value,
                }
            )
            produced.append((position, action, entity_id))
        per_turn.append(produced)

    return steps


def generate(
    spec: dict,
    adapter: EnvAdapter,
    action_ids: list[str],
    timesteps: int,
    max_actions_per_t: int,
    p_invalid: float,
    p_open: float,
    idx: int,
) -> tuple[Any, Any, list[list[dict]]]:
    """Return (pristine seed, expected final state, timeline grouped by timestep)."""
    actions = _parse(spec, action_ids)
    stateful = [a for a in actions if not a.open_ended]
    open_actions = [a for a in actions if a.open_ended]
    enforceable = [a for a in stateful if a.enforced]

    rng = Random(idx)
    sim = adapter.initial_state(rng)  # mutated during simulation -> expected final state
    seed = adapter.initial_state(Random(idx))  # identical pristine copy for the task

    timeline: list[list[dict]] = []
    for _ in range(timesteps):
        group: list[dict] = []
        for _ in range(rng.randint(1, max_actions_per_t)):
            # Open-ended (e.g. DeepWiki): emit a placeholder slot the LLM fills later.
            # No state effect, no API call here — nondeterministic, judged separately.
            if open_actions and rng.random() < p_open:
                action = rng.choice(open_actions)
                group.append(
                    {
                        "action": action.id,
                        "tool": action.tool,
                        "kind": action.kind,
                        "open_ended": True,
                        "objects": {},
                        "args": {},
                        "expect_error": False,
                        "entity_id": None,
                    }
                )
                continue
            if enforceable and rng.random() < p_invalid:
                action = rng.choice(enforceable)
                object_id = adapter.invalid_ref(action.object_type)
                kind = "invalid"
            else:
                available = [
                    a
                    for a in stateful
                    if a.object_type is None or adapter.objects_of_type(sim, a.object_type)
                ]
                action = rng.choice(available)
                object_id = (
                    rng.choice(adapter.objects_of_type(sim, action.object_type))
                    if action.object_type
                    else None
                )
                kind = action.kind
            outcome = adapter.apply(action.id, object_id, sim, rng)
            # Generation invariant: the drawn validity must match what the tool did.
            assert outcome.error == (kind == "invalid"), (action.id, object_id, outcome)
            group.append(
                {
                    "action": action.id,
                    "tool": action.tool,
                    "kind": kind,
                    "open_ended": False,
                    # Every entity-ref arg (for multi-entity matching), value args excluded.
                    "objects": {p: outcome.args[p] for p in action.ref_params if p in outcome.args},
                    "args": outcome.args,
                    "expect_error": outcome.error,
                    "entity_id": outcome.entity_id,
                }
            )
        timeline.append(group)
    return seed, sim, timeline
