"""Stages 3, 4, 5 and 7 — inventing the world the sequence needs.

The order matters and is not arbitrary:

3. **Core entities.** The sequence says it needs a chat, two people and a message it can react
   to. This invents them, coherently, as one situation. The task acquires its semantics here.
4. **Reference properties.** Each core entity is given one way of being described instead of
   named. The model chooses which; the adapter works out what goes in it and proves the result
   singles that entity out.
5. **Population.** Filler is added so the world reads lived-in — one entity at a time, each
   kept only if every reference property still resolves to exactly its own entity.
7. **Content.** Once the world is concrete (and, by then, replayed), the free-text
   placeholders are filled.

Stage 7 sits last because it is the only stage whose output cannot invalidate anything:
`signature` excludes text, so content can be decided after the expected state is known.
"""

from my_env2.adapter import ChatAdapter
from my_env2.llm import Author, AuthoringError
from my_env2.render import manifest_brief, shared_context, symbolic_steps
from my_env2.seed import WorldDraft, build, summarise, summarise_draft
from my_env2.spec import ReferenceMode, reference_modes
from my_env2.state import ChatState
from my_env2.symbolic import Sequence

_ENTITIES_SYSTEM = """You invent the small world an agent task takes place in.

You are given an environment, a plan of actions an agent will be asked to perform, and a list \
of PLACEHOLDERS the plan refers to. A placeholder is something that has to already exist \
before the agent starts. Invent each one, together with whatever else is needed to make the \
whole thing read like one real situation: a handful of colleagues, a couple of conversations, \
and enough history that the plan is a sensible thing to ask.

Write the world, not the task. Nobody in it knows an agent is coming, and above all the work is \
NOT already done: never write a message that carries out a step of the plan, and never write one \
that states the answer to something the plan asks. If the history already contains the answer, \
there is nothing left to ask for and the task measures nothing.

RULES
- Bind every placeholder exactly once, to an entity of the right type, via its `symbol` field. \
Leave `symbol` null on everything else.
- Honour every REQUIRED line. They are not suggestions; a task that violates one measures \
nothing.
- You already exist, as @you. Never add a `users` entry for yourself, and never list yourself in \
a `members` array — you are a member of every conversation automatically.
- Every handle must differ from every other. Display names may repeat; handles never do.
- `sender` is a local user key, or the literal "actor" for yourself. It must be one of the \
`members` of the conversation the message is in — people do not post in rooms they are not in. \
The same goes for `reactors`, and you are never one of them.
- `reply_to` must name a message in the SAME conversation with a lower `order`.
- `order` is a small integer placing the message on one shared clock across all \
conversations, so the history interleaves.
- `read_by_actor` false means you have not caught up on that message yet.
- Never write the same message twice. Each one has to say something none of the others does — \
that is what makes it possible to point at one of them later.
- Keep it small and specific: 3-6 other people, 2-4 conversations, 6-14 messages. Give people \
ordinary names and real-looking handles. Make the messages say something — a decision being \
argued about, a number someone pulled, a question left hanging — never filler like "Hi" or \
"Sounds good".

Respond with ONLY this JSON object:
{"topic": "<one line: what this workspace is dealing with>",
 "actor_name": "<your display name>",
 "users":    [{"ref": "u1", "name": "...", "handle": "...", "symbol": null}],
 "chats":    [{"ref": "c1", "name": "..." or null, "members": ["u1"], "symbol": null}],
 "messages": [{"ref": "m1", "chat": "c1", "sender": "u1", "text": "...", "order": 1,
               "reply_to": null, "read_by_actor": true, "reactors": [],
               "reaction_emoji": ":+1:", "symbol": null}]}"""

_REFERENCES_SYSTEM = """You decide how a task will refer to things without naming their ids.

You are given a workspace and, for each entity the task is about, the ways it could be picked out \
by description. Pick the ONE that suits that entity best, and say only which. What goes into it is \
worked out from the workspace afterwards, so you do not have to supply or check anything.

Judge it on how the finished sentence would read and on how much work it makes the reader do. \
Describing what someone did, or what a conversation is about, is better than restating a name or a \
handle — those tell the reader nothing they could not have been handed. Some modes will not fit \
the entity in front of you at all; say so by choosing a different one.

Respond with ONLY this JSON object, one entry per entity:
{"references": [{"symbol": "$chat_0", "mode": "<mode id>"}]}"""

_POPULATE_SYSTEM = """You pad out a workspace so it looks lived-in.

You are given a workspace that was built around one specific task. It is too tidy: everything \
in it is there for a reason, which is itself a giveaway. Add ordinary, unrelated traffic — a \
few more colleagues, another conversation or two, and messages that have nothing to do with \
anything.

Put most of the new messages in the conversations that already exist, from the people already \
in them. A separate room full of strangers hides nothing; unrelated chatter alongside the real \
thing does.

Three hard rules:
- Do NOT touch or restate what is already there. You are only adding.
- Refer to existing people, conversations and messages by the SHORT KEY shown on the left of \
each line (`u2`, `c1`, `m4`) — never by a name or by anything else. New entries you add get \
their own new keys.
- Each CONDITION listed below must still pick out exactly the entity it picks out now. If \
adding a person whose handle collides, or a message repeating a distinctive phrase, would make \
a condition match two things, do not add it. Anything that breaks a condition is discarded, so \
being careless here just wastes your work.

Give messages `order` values spread across the existing range so the new history interleaves \
with the old rather than piling up after it. A reply must have a higher `order` than the message \
it replies to.

Every entry you return is a NEW one and needs a key nothing else uses — start them all with "n". \
Do not return an entry for anything already in the workspace; it is already there, and repeating \
it is the one thing that makes this call useless.

Respond with ONLY this JSON object:
{"new_users": [{"ref": "n1", "name": "...", "handle": "..."}],
 "new_chats": [{"ref": "n2", "name": "...", "members": ["u1", "n1"]}],
 "new_messages": [{"ref": "n3", "chat": "c1", "sender": "u2", "text": "...", "order": 4,
                   "reply_to": null, "read_by_actor": true, "reactors": []}]}"""

_CONTENT_SYSTEM = """You write the text a task's steps carry.

You are given a workspace, a plan of what the agent will do in it, and a list of PLACEHOLDERS \
for the free text in that plan. Fill each one so that the whole thing reads like one errand a \
colleague actually asked for.

- A message body should sound like the person you act as, addressed to the people in that \
conversation, and should belong to what is being discussed there.
- Where a step says its text must CARRY what an earlier step returned, there is no placeholder \
for it — the agent supplies that itself. Write the surrounding placeholders so they fit \
alongside it.
- For a repository question, name a real, well-known public GitHub repo in owner/repo form and \
ask something specific whose answer does not change: what the project is for, how a named \
component works, what a term in it means. NEVER ask about maintainers, contributors, stars, \
versions or anything else a release could move — a stored expectation for those goes stale and \
the task starts marking correct answers wrong. Read the step's `returns` line too: each tool \
answers a different range of things, and a question outside its range has no obtainable answer \
at all.
- Keep every value short. A message is a sentence or two, not a paragraph.

Respond with ONLY this JSON object, one entry per placeholder, keyed by placeholder:
{"content": {"$text_0": "...", "$name_1": "..."}}"""


def author_world(
    author: Author, spec: dict, sequence: Sequence
) -> tuple[WorldDraft, str]:
    """Stage 3. `(draft, shared context)` — the context is reused by every later stage."""
    context = shared_context(spec, sequence)
    request = "\n\n".join(
        [
            context,
            "PLAN THE AGENT WILL BE ASKED TO CARRY OUT\n"
            + symbolic_steps(spec, sequence),
            "PLACEHOLDERS THAT MUST ALREADY EXIST\n" + manifest_brief(sequence),
            "BIND EXACTLY THESE, ONE EACH, AND NOTHING ELSE\n  "
            + ", ".join(
                f"{entry.symbol} (a {entry.entity_type})"
                for entry in sequence.manifest
                if entry.origin == "seed"
            ),
        ]
    )
    required = sequence.seed_entities()

    def buildable(reply: dict) -> None:
        # The check IS the build: a world is acceptable exactly when it produces a state
        # satisfying the sequence, so there is nothing to verify separately.
        build(WorldDraft.model_validate(reply), required)

    reply = author.ask(sequence.task_id, "world", _ENTITIES_SYSTEM, request, buildable)
    return WorldDraft.model_validate(reply), context


def assign_references(
    author: Author,
    spec: dict,
    sequence: Sequence,
    adapter: ChatAdapter,
    state: ChatState,
    binding: dict[str, str],
    context: str,
) -> dict[str, dict]:
    """Stage 4. `symbol -> {mode, params, phrase, predicate}` for every core entity.

    The model chooses **which** mode; the adapter works out what goes in it and proves that the
    result singles the entity out. A mode that cannot be made to fit is skipped and the next one
    tried, in the model's order first and then in declared order — which runs most indirect first,
    so a reference nobody chose still asks the agent to work something out.

    That division is what makes the stage total, and totality is the requirement: Stage 9 strips
    ids out of the prompt, so an entity without a working reference does not yield a harder task
    but an unanswerable one.
    """
    modes = reference_modes(spec)
    core = [entry for entry in sequence.manifest if entry.origin == "seed"]
    lines = []
    for entry in core:
        target = binding[entry.symbol]
        lines.append(f"  {entry.symbol} = {target} ({adapter.describe(state, target)})")
        for mode in modes[entry.entity_type]:
            lines.append(
                f'      mode {mode.id}: reads as "{mode.phrase}" — {mode.predicate}'
            )

    request = "\n\n".join(
        [
            context,
            "WORKSPACE\n" + summarise(state),
            "ENTITIES TO DESCRIBE, AND THE MODES AVAILABLE FOR EACH\n"
            + "\n".join(lines),
        ]
    )
    try:
        reply = author.ask(sequence.task_id, "references", _REFERENCES_SYSTEM, request)
        proposed = {
            item["symbol"]: item
            for item in reply.get("references") or []
            if isinstance(item, dict) and "symbol" in item
        }
    except Exception:  # noqa: BLE001 - the deterministic path below covers every entity anyway
        proposed = {}

    by_id = {mode.id: mode for group in modes.values() for mode in group}
    references: dict[str, dict] = {}
    for entry in core:
        target = binding[entry.symbol]
        choice = proposed.get(entry.symbol, {}).get("mode")
        for mode in _preference(modes[entry.entity_type], by_id.get(choice)):
            params = adapter.mode_params(state, mode.id, target)
            if params is None:
                continue
            references[entry.symbol] = {
                "mode": mode.id,
                "params": params,
                "phrase": mode.render(params),
                "predicate": mode.predicate.format(**params),
                "proposed": choice,
            }
            break
        else:
            raise AuthoringError(
                f"{sequence.task_id}: no reference mode singles out {entry.symbol} "
                f"({target}); the world is too uniform to describe it"
            )
    return references


def populate(
    author: Author,
    spec: dict,
    sequence: Sequence,
    adapter: ChatAdapter,
    core: WorldDraft,
    references: dict[str, dict],
    context: str,
) -> tuple[WorldDraft, list[str]]:
    """Stage 5. `(the populated draft, what was rejected)`.

    Filler is folded in one entity at a time and each addition is kept only if the whole set of
    reference conditions still resolves. Checking after every single addition rather than once
    at the end is what makes the failure mode *dropping one message* instead of *losing the
    batch*.
    """
    conditions = "\n".join(
        f"  {reference['predicate']}  -> must keep matching exactly one {_type_of(sequence, symbol)}"
        for symbol, reference in references.items()
    )
    request = "\n\n".join(
        [
            context,
            "WORKSPACE SO FAR\n" + summarise_draft(core),
            "CONDITIONS\n" + conditions,
        ]
    )
    taken = {entity.ref for entity in (*core.users, *core.chats, *core.messages)}

    def adds_something(reply: dict) -> None:
        """A reply that only restates the world is the failure mode worth naming.

        Asked to add to a world, a model will hand the world straight back — every entry keyed to
        something that already exists, so every one is rejected as a duplicate and the stage
        yields nothing while appearing to have run. The separate `new_*` keys make the intent
        harder to miss, and this makes the miss a correction round instead of silence.
        """
        extra = _additions(reply)
        fresh = [
            entity
            for entity in (*extra.users, *extra.chats, *extra.messages)
            if entity.ref not in taken
        ]
        if not fresh:
            raise AuthoringError(
                "every entry you returned reuses a key that already exists, so nothing was "
                "added. Return only NEW people, chats and messages, each with a new key"
            )

    try:
        reply = author.ask(
            sequence.task_id, "populate", _POPULATE_SYSTEM, request, adds_something
        )
        extra = _additions(reply)
    except Exception:  # noqa: BLE001 - a world without padding is weaker, not broken
        return core, [
            "stage 5 produced nothing usable; the task keeps the core world only"
        ]

    required = sequence.seed_entities()
    accepted, rejected = core, []
    # Messages go in clock order rather than list order: `build` validates a reply against the
    # clock, so a child listed before its parent would be rejected on its own and accepted as
    # part of the whole — which would silently unthread filler conversations.
    for kind, item in [
        *[("users", item) for item in extra.users],
        *[("chats", item) for item in extra.chats],
        *[("messages", item) for item in sorted(extra.messages, key=lambda m: m.order)],
    ]:
        item.symbol = None  # filler never claims a placeholder, whatever it was told
        candidate = accepted.model_copy(deep=True)
        getattr(candidate, kind).append(item)
        try:
            state, binding = build(candidate, required)
            broken = next(
                (
                    symbol
                    for symbol, reference in references.items()
                    if adapter.resolve(state, reference["mode"], reference["params"])
                    != [binding[symbol]]
                ),
                None,
            )
        except Exception as error:  # noqa: BLE001 - one bad addition, not a lost world
            rejected.append(f"{kind[:-1]} {item.ref}: {error}")
            continue
        if broken:
            rejected.append(
                f"{kind[:-1]} {item.ref}: would make {references[broken]['predicate']!r} "
                f"stop singling out {broken}"
            )
            continue
        accepted = candidate
    return accepted, rejected


def author_content(
    author: Author,
    sequence: Sequence,
    state: ChatState,
    steps_text: str,
    context: str,
) -> dict[str, str]:
    """Stage 7. `content placeholder -> the text authored for it`."""
    slots = [slot for slot in sequence.slots if slot.kind == "content"]
    if not slots:
        return {}
    by_key = {step.key: step for step in sequence.steps}
    lines = [
        f"  {by_key[slot.key].content[slot.param]} — step {sequence.number(slot.key)} "
        f"({by_key[slot.key].action}.{slot.param}): {slot.description}"
        for slot in slots
    ]
    request = "\n\n".join(
        [
            context,
            "WORKSPACE\n" + summarise(state),
            "PLAN\n" + steps_text,
            "PLACEHOLDERS TO FILL\n" + "\n".join(lines),
        ]
    )
    wanted = {by_key[slot.key].content[slot.param] for slot in slots}

    def complete(reply: dict) -> None:
        content = reply.get("content")
        if not isinstance(content, dict):
            raise AuthoringError('the reply had no "content" object in it')
        if missing := sorted(wanted - set(content)):
            raise AuthoringError(
                f"nothing was written for {', '.join(missing)}; every placeholder needs an "
                "entry under its exact key"
            )

    reply = author.ask(sequence.task_id, "content", _CONTENT_SYSTEM, request, complete)
    return {key: str(value) for key, value in reply["content"].items() if key in wanted}


def _type_of(sequence: Sequence, symbol: str) -> str:
    return sequence.entry(symbol).entity_type


def _additions(reply: dict) -> WorldDraft:
    """Stage 5's reply as a draft. Its keys are `new_*` so that "these are additions" is part of
    the shape rather than only part of the instructions."""
    return WorldDraft.model_validate(
        {
            "users": reply.get("new_users") or [],
            "chats": reply.get("new_chats") or [],
            "messages": reply.get("new_messages") or [],
        }
    )


def _preference(
    modes: list[ReferenceMode], first: ReferenceMode | None
) -> list[ReferenceMode]:
    """The model's choice, then every other mode as a fallback in declared order."""
    return (
        [first, *[mode for mode in modes if mode is not first]]
        if first
        else list(modes)
    )
