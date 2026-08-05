"""What the authoring model is shown.

Stage 2's shared context lives here, and so do the two renderings of a sequence that the
later stages need: the *symbolic* one, which describes a world that does not exist yet, and
the *concrete* one, which describes the same steps once the world has been built and every
placeholder resolved.

Every word of English in here comes from the spec — an action's `description`, a param's
`description`, an entity type's `description`, an action's `returns` — or from the adapter's
`describe`. Nothing knows this environment is a chat app, which is what lets the same
renderer serve a different spec.
"""

from my_env2.spec import Action, parse_actions
from my_env2.symbolic import ManifestEntry, Sequence, Step


def shared_context(spec: dict, sequence: Sequence) -> str:
    """Stage 2. Built once per task and handed to every authoring call after it, so that all
    of them decide against the same account of what the environment means."""
    actions = {action.id: action for action in parse_actions(spec)}
    used = list(dict.fromkeys(step.action for step in sequence.steps))
    types = list(dict.fromkeys(entry.entity_type for entry in sequence.manifest))

    lines = ["ENVIRONMENT"]
    for name, server in spec.get("servers", {}).items():
        lines.append(f"  {name}: {server['description']}")
    actor = spec["_meta"]["actor"]
    lines.append(f"  You act as one specific user. {actor['description']}")

    lines.append("\nENTITY TYPES IN THIS TASK")
    for entity_type in types:
        entry = spec["entities"][entity_type]
        lines.append(f"  {entity_type} — {entry.get('description', '')}")
        for field, kind in entry["fields"].items():
            lines.append(f"      {field}: {kind}")

    lines.append("\nACTIONS THIS TASK USES")
    for action_id in used:
        action = actions[action_id]
        lines.append(f"  {action.id} ({action.kind}) — {action.description}")
        for param in action.params:
            required = "" if param.get("required") else " (optional)"
            lines.append(f"      {param['name']}: {param['description']}{required}")
        if action.returns:
            lines.append(f"      returns: {action.returns}")
    return "\n".join(lines)


def manifest_brief(sequence: Sequence) -> str:
    """The seed entities the sequence needs, and what it needs of them. Rollout entities are
    left out: the agent creates those, so there is nothing to invent."""
    lines = []
    for entry in sequence.manifest:
        if entry.origin != "seed":
            continue
        lines.append(f"  {entry.symbol} — a {entry.entity_type}")
        for role in entry.roles:
            lines.append(
                f"      step {sequence.number(role['step'])} uses it as "
                f"{role['action']}.{role['param']} ({role['description']})"
            )
        for requirement in entry.requirements:
            lines.append(f"      REQUIRED: {requirement}")
    return "\n".join(lines)


def symbolic_steps(spec: dict, sequence: Sequence) -> str:
    """The plan while the world is still hypothetical: placeholders, not ids."""
    actions = {action.id: action for action in parse_actions(spec)}
    lines = []
    for number, step in enumerate(sequence.steps, start=1):
        action = actions[step.action]
        # The tag ADDS to the kind rather than replacing it: an aside still writes to the
        # environment, and an author told only "distractor" drops it — which costs the agent
        # recall for obeying the prompt.
        tag = f"{action.kind}, an aside" if step.unrelated else action.kind
        lines.append(f"step {number} [{tag}] {action.id} — {action.description}")
        lines.extend(_param_lines(sequence, action, step, resolve=None))
        if step.produces_entity:
            lines.append(f"    -> creates {step.produces_entity}")
        elif step.produces_value:
            lines.append(f"    -> returns {step.produces_value}: {action.returns}")
    return "\n".join(lines)


def concrete_steps(
    spec: dict,
    sequence: Sequence,
    describe: dict[str, str],
    content: dict[str, str],
    observed: dict[str, str],
) -> str:
    """The plan once the world exists: real entities described, authored content inlined.

    `describe` maps a symbol to a line about the entity behind it, `content` maps a content
    placeholder to the text authored for it, and `observed` maps a step key to what that step
    actually returned during replay — which is what makes a carry requirement checkable.
    """
    actions = {action.id: action for action in parse_actions(spec)}
    lines = []
    for number, step in enumerate(sequence.steps, start=1):
        action = actions[step.action]
        tag = f"{action.kind}, an aside" if step.unrelated else action.kind
        lines.append(f"step {number} [{tag}] {action.id} — {action.description}")
        lines.extend(_param_lines(sequence, action, step, resolve=(describe, content)))
        if step.produces_entity:
            lines.append("    -> creates something new")
        elif step.key in observed:
            lines.append(f"    -> returns: {_clip(observed[step.key])}")
        elif step.produces_value:
            lines.append(
                f"    -> returns {action.returns} (not known until the agent runs it)"
            )
    return "\n".join(lines)


def _param_lines(
    sequence: Sequence,
    action: Action,
    step: Step,
    resolve: tuple[dict[str, str], dict[str, str]] | None,
) -> list[str]:
    lines = []
    for param, value in step.refs.items():
        symbols = value if isinstance(value, list) else [value]
        if resolve is None:
            rendered = ", ".join(_symbol_note(sequence, symbol) for symbol in symbols)
        else:
            rendered = ", ".join(resolve[0].get(symbol, symbol) for symbol in symbols)
        lines.append(f"    {param:12} = {rendered}")
    for param, symbol in step.content.items():
        written = resolve[1].get(symbol) if resolve else None
        if written is None:
            # Either the world is still hypothetical, or Stage 7 has not run yet — both want
            # the placeholder shown alongside what it is for.
            description = next(
                p["description"] for p in action.params if p["name"] == param
            )
            lines.append(f"    {param:12} = {symbol} (free text: {description})")
        else:
            lines.append(f"    {param:12} = {written!r}")
    for param, sources in step.carries.items():
        where = " and ".join(f"step {sequence.number(key)}" for key in sources)
        lines.append(f"    {param:12} <- must carry what {where} returned")
    return lines


def _symbol_note(sequence: Sequence, symbol: str) -> str:
    entry: ManifestEntry = sequence.entry(symbol)
    if entry.origin == "rollout":
        return f"{symbol} (the {entry.entity_type} step {sequence.number(entry.created_by)} creates)"
    return f"{symbol} (an existing {entry.entity_type})"


def _clip(text: str, limit: int = 900) -> str:
    return text if len(text) <= limit else text[:limit] + " …(truncated)"
