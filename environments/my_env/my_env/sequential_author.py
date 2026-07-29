"""Render a generated chain batch as a precise, ordered list of steps.

The deterministic half of authoring: it takes the output of `gen_dependency_chains` and lays
out, in order, exactly what has to happen. No LLM is involved.

**Environment-agnostic.** Every word of English comes from the action spec — each action's
`description`, each param's `description`, each action's `returns` — and every structural fact
comes from the spec plus the adapter's existing `initial_state` / `objects_of_type`. Nothing
here knows that this environment is a chat app, so the same renderer serves any spec. The
price is that a step reads as a labelled argument list rather than a sentence; turning that
into prose is the authoring model's job, which is where env-specific phrasing belongs.

Two things make it more than formatting.

**Order.** The generator emits `timelines[chain][turn]`; reading it turn-major —
`(turn, chain, position)` — is automatically a valid topological order, because a source
always sits in a *strictly* earlier turn than whatever consumes it. Nothing needs sorting.

**References.** Every entity an argument names falls into one of three cases, and only the
first can be stated outright:

- it came from the seed, so the agent can find it: name it;
- the rollout created it and an edge says so: "produced by step 2";
- the rollout created it and *no* edge says so. The generator draws unbound arguments from
  everything present when the turn began, which includes what earlier turns created — a real
  dependency it simply did not choose. Around 2% of unbound references are like this.

That third case is why references are classified against the seed state rather than by reading
`depends_on`. Trusting the edge list would print a bare id for something the agent cannot know
in advance, and the task would be unsolvable.
"""

from random import Random
from typing import Any

from my_env.generate import EnvAdapter, _parse


def _join(parts: list[str]) -> str:
    if len(parts) <= 1:
        return parts[0] if parts else ""
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _linearise(timelines: list[list[list[dict]]]) -> list[dict]:
    """Flatten turn-major. Valid as-is: nothing depends on its own turn or a later one."""
    steps: list[dict] = []
    for turn in range(len(timelines[0]) if timelines else 0):
        for timeline in timelines:
            steps.extend(timeline[turn])
    return steps


def render_steps(spec: dict, adapter: EnvAdapter, example: dict) -> list[str]:
    """One block per action, in an order the agent can follow, as `step N ...` text.

    `example` is one entry of a batch from `gen_dependency_chains` — it needs `seed_idx` and
    `timelines`. The seed state is rebuilt through the adapter rather than stored, since
    `initial_state` is deterministic in that seed.
    """
    entries = {entry["id"]: entry for entry in spec["actions"]}
    actions = {action.id: action for action in _parse(spec, list(entries))}
    steps = _linearise(example["timelines"])
    numbers = {step["key"]: number for number, step in enumerate(steps, start=1)}

    # What already existed, and of what type — both read through the adapter, so this stays
    # generic over environments.
    seed = adapter.initial_state(Random(example["seed_idx"]))
    seeded: dict[str, str] = {
        entity_id: entity_type
        for entity_type in spec.get("entities", {})
        for entity_id in adapter.objects_of_type(seed, entity_type)
    }

    # Which step brought each new entity into being. Only actions that `produce` an entity
    # create anything; one that reports an entity it merely affected must not be credited,
    # so `setdefault` keeps the creator.
    created: dict[str, tuple[int, str]] = {}
    for number, step in enumerate(steps, start=1):
        produces = actions[step["action"]].produces or {}
        entity_id = step["entity_id"]
        if entity_id and entity_id not in seeded and produces.get("kind") == "entity":
            created.setdefault(entity_id, (number, produces["type"]))

    def reference(entity_id: Any) -> str:
        if entity_id in seeded:
            return f"{entity_id} (a {seeded[entity_id]} that already exists)"
        if entity_id in created:
            number, entity_type = created[entity_id]
            return f"the {entity_type} produced by step {number}"
        return str(entity_id)

    blocks = []
    for number, step in enumerate(steps, start=1):
        entry, action = entries[step["action"]], actions[step["action"]]
        lines = [f"step {number}  [{entry['kind']}]  {entry['id']} — {entry['description']}"]

        # Edges are grouped by the param they land on: several sources may share one param,
        # but only ever one param per edge set.
        by_param: dict[str, list[tuple[str, int]]] = {}
        for edge in step["depends_on"]:
            by_param.setdefault(edge["param"], []).append((edge["via"], numbers[edge["source"]]))

        for param in entry["params"]:
            name = param["name"]
            if step["open_ended"]:
                # No args were sampled: this action is a slot the authoring step fills.
                lines.append(f"    {name:12} ?  supplied by the author — {param['description']}")
                continue
            if name not in step["args"]:
                continue  # left at its default
            if name in by_param:
                sources = sorted({source for _, source in by_param[name]})
                via = by_param[name][0][0]
                if via == "object":
                    produced = actions[steps[sources[0] - 1]["action"]].produces
                    lines.append(f"    {name:12} <- the {produced['type']} produced by "
                                 f"step {sources[0]}")
                else:
                    lines.append(f"    {name:12} <- must carry what "
                                 f"{_join([f'step {s}' for s in sources])} returned")
            elif name in action.ref_params:
                value = step["args"][name]
                rendered = ([reference(one) for one in value] if isinstance(value, list)
                            else [reference(value)])
                lines.append(f"    {name:12} =  {_join(rendered)}")
            else:
                # Not an entity reference, so it is content — and the generator does not
                # choose content. The recorded value is a self-describing placeholder.
                lines.append(f"    {name:12} =  {step['args'][name]!r}  (placeholder — the "
                             f"author decides: {param['description']})")

        if step["open_ended"]:
            lines.append(f"    returns      {entry['returns']}")
        blocks.append("\n".join(lines))
    return blocks
