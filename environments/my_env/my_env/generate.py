"""Environment-agnostic action-sequence generator (see ../DESIGN.md).

Reads an action spec and drives a deterministic random walk through an environment via
an adapter. Env specifics — state, tools, seeding, value args, id minting — live behind
the adapter; this module knows nothing about any particular environment.
"""

from dataclasses import dataclass
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
            )
        )
    return parsed


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
