"""Stage 1 — symbolic sequence generation.

The walker builds a dependency DAG of actions **without a world to walk through**. Where the
stateful generator resolved every object id out of a live simulator, this one mints a typed
placeholder (`$chat_0`) and records what the sequence needs of it. The environment is then
authored to satisfy the sequence, rather than the sequence being whatever a fixed seed
happened to permit.

Removing the simulator removes the only reason a thread could stall on feasibility: any
object an action wants can be conjured. A thread now stops for exactly one reason — nothing
in the pool offers what it could consume next.

What survives from the stateful walker, unchanged in intent:

- **Threads terminate, they do not raise.** A thread out of moves stops where it is.
- **Sinks are unrestricted.** A thread may continue past a non-producing action, because its
  next link can consume some other thread's output.
- **Edges are keyed, never positional.** `{"source": "c0a1", ...}` survives reordering;
  offsets would silently shift.
- **The pool holds only strictly earlier turns**, so nothing depends on a same-turn sibling.
  The stateful walker needed a `frozen` snapshot to guarantee that, because its other source
  of objects was a live simulator. Symbolic minting creates no dependency at all, so the
  pool's own rule is now the whole story.

Two guards are new, and they exist because the earlier pipeline measurably wasted steps.
8.7% of its write links wrote a fact that was already true, which the reward cannot
distinguish from doing nothing:

- **No repeated write pair.** An action carrying `meaningful_when` is never applied twice to
  the same entity. That was every duplicate `add_reaction`.
- **History-dependent actions never consume a rollout-created entity.** `mark_read` on a chat
  the agent created moments ago marks nothing, since the only messages in it are the agent's
  own. Declared per-action in the spec (`requires_history`), so the rule stays generic.

Both are structural: they hold by construction rather than by simulating and checking after.
"""

from collections import Counter
from dataclasses import dataclass, field
from random import Random

from my_env2.spec import Action, Slot, consumer_index, parse_actions


@dataclass
class ChainConfig:
    """How one thread behaves. Every field is per-thread, so threads can differ."""

    max_depth: int = 3
    """How many dependent links this thread aims for. It stops early — without failing — if
    nothing in the pool can be consumed."""
    max_breadth: int = 1
    """Cap on how many earlier outputs a SINGLE action may consume. Sampled once a feasible
    action is chosen, then clamped by how many compatible outputs exist, and again by the
    slot's `arity` (a slot declared `one` always takes exactly one)."""
    p_skip: float = 0.0
    """Chance this thread stays silent for a whole turn. Silence is what lets it wait for
    another thread to produce something it can use."""
    p_cross: float = 0.3
    """Chance this action may borrow from OUTSIDE its own thread. At 0.0 the thread reads as
    one self-contained errand; at 1.0 the whole pool is fair game and — most of the pool
    belonging to other threads — it mostly consumes their work. Rolled per action, and never
    overridden: a thread that finds nothing it is allowed to consume stops early rather than
    reaching outside anyway."""
    p_unrelated: float = 0.0
    """Chance of also emitting an action that depends on nothing — a distractor sub-task. It
    does not count toward depth and is not a link in the dependency chain."""


@dataclass
class Step:
    """One action, with every id still symbolic.

    The three param dicts are kept apart rather than merged into one `args` because they are
    filled by three different things: `refs` by binding at replay, `content` by the authoring
    pass, `carries` by the agent at rollout time (and only a judge can check it).
    """

    key: str
    chain: int
    turn: int
    action: str
    tool: str
    kind: str  # "read" | "write"
    external: bool
    refs: dict[str, str | list[str]] = field(default_factory=dict)
    """param -> symbolic entity id, or a list of them for an `entities_exist` param."""
    content: dict[str, str] = field(default_factory=dict)
    """param -> content placeholder (`$text_0`), filled in Stage 7."""
    carries: dict[str, list[str]] = field(default_factory=dict)
    """param -> the step keys whose returned information must end up in it."""
    produces_entity: str | None = None
    """Symbol of the entity this step creates during the rollout."""
    produces_value: str | None = None
    """Symbol of the information this step returns."""
    depends_on: list[dict] = field(default_factory=list)
    unrelated: bool = False


@dataclass
class ManifestEntry:
    """One symbolic entity and everything the sequence demands of it."""

    symbol: str
    entity_type: str
    origin: (
        str  # "seed" (must exist before the rollout) | "rollout" (the agent creates it)
    )
    created_by: str | None = None  # step key, for a rollout entity
    roles: list[dict] = field(default_factory=list)
    """[{step, action, param, kind, description}] — every place the sequence touches it."""
    requirements: list[str] = field(default_factory=list)
    """What has to be true of it for the steps above to be worth performing. Sourced from the
    spec, so this stays generic: an action's own description plus any `meaningful_when`."""


@dataclass
class Sequence:
    """Stage 1's whole output. No seed and no expected state: neither exists yet."""

    task_id: str
    timelines: list[list[list[Step]]]
    """`timelines[thread][turn]` — what a thread did at a turn, empty when it skipped or had
    finished. Every timeline has the same length, so a turn index means the same thing across
    threads."""
    steps: list[Step]
    """The same steps flattened turn-major, which is already a valid topological order: a
    source always sits in a strictly earlier turn than anything consuming it."""
    manifest: list[ManifestEntry]
    slots: list[Slot]
    shape: dict
    """Realized structure, not the configured intent — a thread truncates silently, so only
    measured values are usable for difficulty analysis."""

    def step(self, key: str) -> Step:
        return next(step for step in self.steps if step.key == key)

    def number(self, key: str) -> int:
        """1-based position in the linear order, which is how prompts refer to a step."""
        return next(i for i, step in enumerate(self.steps, 1) if step.key == key)

    def entry(self, symbol: str) -> ManifestEntry:
        return next(entry for entry in self.manifest if entry.symbol == symbol)

    def seed_entities(self) -> dict[str, str]:
        """Symbol -> entity type, for everything the world must already contain. This is the
        contract the authoring stages have to satisfy and `seed.build` checks against."""
        return {
            entry.symbol: entry.entity_type
            for entry in self.manifest
            if entry.origin == "seed"
        }


@dataclass
class _Produced:
    """One earlier step later ones can draw from."""

    key: str
    chain: int
    turn: int
    offer: tuple[str, str]
    symbol: str | None
    """The entity it created, for an object edge; None for an info producer."""
    creates_entity: bool
    """Whether this offer is an entity the rollout brings into being. Only meaningful when
    `symbol` is set — an info offer is not an entity at all, so a `requires_history` rule over a
    value slot would need a different question asked (does the *source's* subject pre-date the
    rollout), not this flag."""


@dataclass
class _Thread:
    config: ChainConfig
    turns: list[list[Step]] = field(default_factory=list)
    depth: int = 0
    active: bool = True
    emitted: int = 0  # only for minting keys


def generate_sequence(
    spec: dict,
    rng: Random,
    configs: list[ChainConfig],
    *,
    task_id: str = "t0",
    p_reuse: float = 0.5,
    max_global_depth: int | None = None,
    max_turns: int = 200,
) -> Sequence:
    """Walk `len(configs)` interleaved threads over a shared clock, symbolically.

    Generation stops when every thread is finished, or as soon as any thread reaches
    `max_global_depth`. That cap is **off** unless asked for: setting it halts the whole batch
    the moment one thread arrives, truncating every slower thread — and with any skipping at
    all, the threads that lose depth are systematically the ones that skipped. `max_turns` is
    a backstop against a pathological run of skips, not a tuning knob.

    `p_reuse` is the chance that an unbound entity param reuses a seed entity the sequence has
    already asked for instead of minting a fresh one. Reuse is what makes two steps touch the
    same thing, which is both a smaller world to author and the only way a later prompt can
    say "that chat" and mean something.
    """
    if not configs:
        raise ValueError("need at least one chain config")
    if any(config.max_depth < 1 for config in configs):
        raise ValueError("every chain needs max_depth >= 1")
    if any(config.max_breadth < 1 for config in configs):
        raise ValueError("every chain needs max_breadth >= 1")

    actions = parse_actions(spec)
    consumers = consumer_index(actions)
    producers = [action for action in actions if action.produces]
    by_id = {action.id: action for action in actions}

    threads = [_Thread(config=config) for config in configs]
    pool: list[_Produced] = []  # everything produced in STRICTLY earlier turns
    manifest: dict[str, ManifestEntry] = {}
    slots: list[Slot] = []
    counters: Counter = Counter()
    # (action id, symbol) pairs already written by an action that can only be worth doing
    # once. A second one writes a fact that is already true.
    written: set[tuple[str, str]] = set()
    # Actions with nothing to vary — no entity to name, no text to write — have exactly one
    # possible invocation, so emitting one twice is literally the same call again.
    invariant = {
        action.id
        for action in actions
        if not action.refs and not action.content_params()
    }
    emitted_once: set[str] = set()

    def choosable(candidates: list[Action]) -> list[Action]:
        # Falls back to the unfiltered list only if every candidate has already been used,
        # which cannot happen while any action takes an argument — it is here so the caller
        # never has to sample from an empty pool.
        return [
            action for action in candidates if action.id not in emitted_once
        ] or candidates

    def mint(prefix: str) -> str:
        symbol = f"${prefix}_{counters[prefix]}"
        counters[prefix] += 1
        return symbol

    def declare(
        symbol: str, entity_type: str, origin: str, created_by: str | None = None
    ) -> None:
        if symbol not in manifest:
            manifest[symbol] = ManifestEntry(
                symbol=symbol,
                entity_type=entity_type,
                origin=origin,
                created_by=created_by,
            )

    def record_role(symbol: str, step: Step, action: Action, param: str) -> None:
        entry = manifest[symbol]
        entry.roles.append(
            {
                "step": step.key,
                "action": action.id,
                "param": param,
                "kind": action.kind,
                "description": action.description,
            }
        )
        for requirement in action.meaningful_when:
            if (
                requirement["ref"] == param
                and requirement["requirement"] not in entry.requirements
            ):
                entry.requirements.append(requirement["requirement"])

    def needs_history(action: Action, param: str) -> bool:
        return any(
            requirement["ref"] == param and requirement.get("requires_history")
            for requirement in action.meaningful_when
        )

    def seed_symbol(
        action: Action, param: str, entity_type: str, exclude: set[str] = frozenset()
    ) -> str:
        """An entity the sequence needs but no step produces: it must be in the seed.

        Reuse is preferred where it is safe, which keeps the authored world small and lets two
        steps genuinely share a subject. `exclude` keeps one list-valued param from naming the
        same entity twice — harmless to the tool, which dedupes, but it reads as a mistake in
        the prompt and it double-counts the entity's roles in the manifest.
        """
        candidates = [
            entry.symbol
            for entry in manifest.values()
            if entry.origin == "seed"
            and entry.entity_type == entity_type
            and entry.symbol not in exclude
            and (action.id, entry.symbol) not in written
        ]
        if candidates and rng.random() < p_reuse:
            return rng.choice(candidates)
        symbol = mint(entity_type)
        declare(symbol, entity_type, "seed")
        return symbol

    def perform(
        action: Action,
        thread_index: int,
        turn: int,
        sources: list[_Produced],
        consume: dict | None,
        *,
        unrelated: bool = False,
    ) -> Step:
        """Emit one action. `sources` is empty for a root or a distractor."""
        thread = threads[thread_index]
        step = Step(
            key=f"c{thread_index}a{thread.emitted}",
            chain=thread_index,
            turn=turn,
            action=action.id,
            tool=action.tool,
            kind=action.kind,
            external=action.external,
            unrelated=unrelated,
        )
        thread.emitted += 1
        if action.id in invariant:
            emitted_once.add(action.id)

        bound_param = consume["param"] if consume else None
        for ref in action.refs:
            if bound_param == ref.param and consume["slot"] == "object":
                symbols = [source.symbol for source in sources]
                if not ref.many and len(symbols) > 1:
                    # Would record edges from sources the binding then throws away — phantom
                    # dependencies in `depends_on` and in the shape metrics.
                    raise ValueError(
                        f"{action.id}.{ref.param} takes one entity but {len(symbols)} were "
                        "offered; a slot fed by several sources must be declared arity: many"
                    )
                step.refs[ref.param] = symbols if ref.many else symbols[0]
            elif ref.many:
                # A list param nothing feeds: ask the seed for a couple of distinct ones.
                chosen: list[str] = []
                for _ in range(rng.randint(1, 2)):
                    chosen.append(
                        seed_symbol(
                            action, ref.param, ref.entity_type, exclude=set(chosen)
                        )
                    )
                step.refs[ref.param] = chosen
            else:
                step.refs[ref.param] = seed_symbol(action, ref.param, ref.entity_type)
            once_only = any(
                requirement["ref"] == ref.param
                for requirement in action.meaningful_when
            )
            for symbol in _as_list(step.refs[ref.param]):
                record_role(symbol, step, action, ref.param)
                if once_only:
                    written.add((action.id, symbol))

        for param in action.content_params():
            name = param["name"]
            if bound_param == name and consume["slot"] == "value":
                step.carries[name] = [source.key for source in sources]
                slots.append(
                    Slot(
                        key=step.key,
                        param=name,
                        kind="carry",
                        description=param["description"],
                        sources=[source.key for source in sources],
                    )
                )
                continue
            # An optional content param is taken up only sometimes: whether a created chat
            # carries a name decides whether it is a group, so always naming one would
            # remove a whole shape from the space.
            if not param.get("required") and rng.random() < 0.5:
                continue
            step.content[name] = mint(name)
            slots.append(
                Slot(
                    key=step.key,
                    param=name,
                    kind="content",
                    description=param["description"],
                )
            )

        if action.produces:
            if action.produces["kind"] == "entity":
                # `new_` marks it as something the rollout brings into being. The authoring
                # stages must bind seed placeholders and nothing else, and a name that says
                # which is which removes a whole class of mistake from that instruction.
                step.produces_entity = mint(f"new_{action.produces['type']}")
                declare(
                    step.produces_entity, action.produces["type"], "rollout", step.key
                )
            else:
                step.produces_value = mint("info")

        step.depends_on = [
            {
                "source": source.key,
                "via": consume["slot"],
                "param": consume["param"],
                "symbol": source.symbol,
            }
            for source in sources
        ]
        return step

    def eligible_options(
        eligible: list[_Produced],
    ) -> list[tuple[tuple[str, str], Action, dict, list[_Produced]]]:
        """Every way this thread could consume something in `eligible`, grouped by offer type
        so a fan-in draws several sources of one type into one slot."""
        available: dict[tuple[str, str], list[_Produced]] = {}
        for produced in eligible:
            available.setdefault(produced.offer, []).append(produced)
        options = []
        for offer, group in available.items():
            for action, consume in consumers.get(offer, []):
                usable = group
                if consume["slot"] == "object":
                    usable = [produced for produced in group if produced.symbol]
                    if needs_history(action, consume["param"]):
                        # In this spec that empties the list every time, since the only entities
                        # on offer are ones the rollout just created. It is written as the
                        # general rule rather than as `[]` because a spec where something offers
                        # a pre-existing entity is the case the rule is actually for.
                        usable = [p for p in usable if not p.creates_entity]
                    usable = [p for p in usable if (action.id, p.symbol) not in written]
                if usable:
                    options.append((offer, action, consume, usable))
        return options

    def consume_one(
        thread_index: int, turn: int, eligible: list[_Produced]
    ) -> Step | None:
        """One link drawing on `eligible`, or None if nothing there can be consumed."""
        options = eligible_options(eligible)
        if not options:
            return None
        config = threads[thread_index].config
        _, action, consume, group = rng.choice(options)
        # Breadth is sampled only once an action is settled on, then clamped twice: by what
        # exists, and by whether the slot can hold more than one thing at all.
        width = 1 if consume["arity"] == "one" else rng.randint(1, config.max_breadth)
        return perform(
            action,
            thread_index,
            turn,
            rng.sample(group, min(width, len(group))),
            consume,
        )

    def root(thread_index: int, turn: int) -> Step:
        """Open a thread's own strand, depending on nothing. Always possible — every object it
        needs is minted.

        A thread that will extend has to open with something that produces, or it has nothing
        to build on. A single-link thread has no such obligation, and letting it open with a
        sink is the only way some actions reach a task at all: `mark_read` needs a chat with
        unread history, which no action can produce, so it can never be a dependent link.
        """
        openings = producers if threads[thread_index].config.max_depth > 1 else actions
        return perform(rng.choice(choosable(openings)), thread_index, turn, [], None)

    def dependent(thread_index: int, turn: int) -> Step | None:
        """The thread's next link, honouring how far outside itself it will look."""
        thread = threads[thread_index]
        own = [produced for produced in pool if produced.chain == thread_index]
        other = [produced for produced in pool if produced.chain != thread_index]
        borrow = rng.random() < thread.config.p_cross

        if thread.depth == 0:
            # Nothing emitted yet. Borrowing means picking up another thread's work, which is
            # what makes a skipped turn meaningful: the thread can wait for output that does
            # not exist yet. Otherwise it opens an errand of its own.
            if borrow and other:
                return consume_one(thread_index, turn, other) or root(
                    thread_index, turn
                )
            return root(thread_index, turn)

        # Already started, so extend the strand rather than restart it: only a thread's FIRST
        # action may depend on nothing, or `depth` would count roots as chain depth.
        return consume_one(thread_index, turn, own + other if borrow else own)

    turn = 0
    while any(thread.active for thread in threads) and turn < max_turns:
        produced_this_turn: list[_Produced] = []
        for index, thread in enumerate(threads):
            emitted: list[Step] = []
            if thread.active and rng.random() >= thread.config.p_skip:
                step = dependent(index, turn)
                if step is None:
                    thread.active = False  # out of consumable offers: stop, do not fail
                else:
                    emitted.append(step)
                    thread.depth += 1
                    if thread.depth >= thread.config.max_depth:
                        thread.active = False
                    if rng.random() < thread.config.p_unrelated:
                        emitted.append(
                            perform(
                                rng.choice(choosable(actions)),
                                index,
                                turn,
                                [],
                                None,
                                unrelated=True,
                            )
                        )
            thread.turns.append(emitted)
            for step in emitted:
                action = by_id[step.action]
                if action.produces:
                    produced_this_turn.append(
                        _Produced(
                            key=step.key,
                            chain=index,
                            turn=turn,
                            offer=action.offer,
                            symbol=step.produces_entity,
                            creates_entity=step.produces_entity is not None,
                        )
                    )
        # Only now do this turn's outputs become consumable, so nothing depends on an action
        # in its own turn and thread order within a turn carries no meaning.
        pool.extend(produced_this_turn)
        turn += 1
        if max_global_depth is not None and any(
            t.depth >= max_global_depth for t in threads
        ):
            break

    timelines = [thread.turns for thread in threads]
    # Turn-major, which is already a valid topological order.
    steps = [
        step
        for turn_index in range(len(timelines[0]))
        for line in timelines
        for step in line[turn_index]
    ]
    return Sequence(
        task_id=task_id,
        timelines=timelines,
        steps=steps,
        manifest=list(manifest.values()),
        slots=slots,
        shape=_shape(steps, threads),
    )


def _as_list(value) -> list[str]:
    return value if isinstance(value, list) else [value]


def _shape(steps: list[Step], threads: list[_Thread]) -> dict:
    """Realized structure. Every number here is measured off the emitted steps rather than read
    back from a config, because a thread truncates silently when it runs out of moves —
    configured depth is an aspiration, and regressing difficulty on an aspiration is useless.

    `links_per_thread` and `longest_chain` are both reported and they are different things. A
    thread's links can all hang off one foreign source, which is a fan-out of depth two however
    many links it has; the longest path through the DAG is what "how deep is this task" means.
    """
    fan_in: Counter = Counter()
    fan_out: Counter = Counter()
    cross = 0
    object_edges = value_edges = 0
    by_key = {step.key: step for step in steps}
    for step in steps:
        if step.depends_on:
            fan_in[len(step.depends_on)] += 1
        for edge in step.depends_on:
            fan_out[edge["source"]] += 1
            if by_key[edge["source"]].chain != step.chain:
                cross += 1
            if edge["via"] == "object":
                object_edges += 1
            else:
                value_edges += 1

    # Longest path to each step. `steps` is already topologically ordered, so one pass does it.
    depth: dict[str, int] = {}
    for step in steps:
        depth[step.key] = 1 + max(
            (depth[edge["source"]] for edge in step.depends_on), default=0
        )
    return {
        "threads": len(threads),
        "turns": len(threads[0].turns) if threads else 0,
        "steps": len(steps),
        "links_per_thread": [thread.depth for thread in threads],
        "longest_chain": max(depth.values(), default=0),
        "longest_chain_per_thread": [
            max((depth[s.key] for s in steps if s.chain == index), default=0)
            for index in range(len(threads))
        ],
        "cross_thread_edges": cross,
        "object_edges": object_edges,
        "value_edges": value_edges,
        "fan_in": dict(sorted(fan_in.items())),
        "fan_out": dict(sorted(Counter(fan_out.values()).items())),
        "external_steps": sum(1 for step in steps if step.external),
        "write_steps": sum(1 for step in steps if step.kind == "write"),
        "distractors": sum(1 for step in steps if step.unrelated),
        "actions": dict(sorted(Counter(step.action for step in steps).items())),
    }
