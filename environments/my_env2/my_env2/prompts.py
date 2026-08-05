"""Stages 8, 9 and 10 — the same task written three ways, plus the judge specification.

The three versions differ only in how much of the work the prompt does for the agent:

- **v1** numbers the steps and names ids. It is the floor you measure everything else against.
- **v2** is prose, and every id is replaced by the description Stage 4 proved singles it out.
  The agent now has to inspect the environment before it can act at all.
- **v3** asks for the goal. No enumerated steps, nothing quoted, nothing that reads like a
  transcription of a plan — a request a colleague would actually send.

`(seed, expected)` is identical across all three, so a score difference between two of them is
attributable to how the task was specified and to nothing else.

The judge specification is authored alongside v1 because that is the version that still states
everything explicitly. **Which** items need judging, and **where** each answer has to be
delivered, are decided here in code rather than asked for: an author free to choose a
destination invents a message the plan does not contain, and the state reward then penalises an
agent for obeying the prompt.
"""

import re

from my_env2.adapter import ChatAdapter
from my_env2.llm import Author, AuthoringError
from my_env2.render import concrete_steps
from my_env2.seed import summarise
from my_env2.spec import parse_actions
from my_env2.state import ChatState
from my_env2.symbolic import Sequence

_V1_SYSTEM = """You turn a plan into a task, written as an explicit numbered sequence.

You are given a workspace, and the exact actions an agent should perform in it with every \
detail already decided. Write the request the agent will receive.

- One numbered step per action, in the given order — but write SENTENCES. The plan you are given \
is a machine listing; do not reproduce its layout, its bracketed tags, its parameter lines or \
its "returns" notes. Those are notes to you. Ask for the thing, using the ids shown.
- Every step is work that must happen, including any marked as an aside. The plan is the \
complete and exact set of actions: never ask for anything it does not contain, and never leave \
one out. An unplanned message is an unexpected change to the workspace, and a missing one costs \
the agent credit for obeying you.
- Where a step's text must CARRY what an earlier step returned, say so plainly: the agent has to \
look that up and say it in the message. Ask for the information, not for a transcript — a person \
asks a colleague to pass on what a thread said, never to paste the raw tool output. Never guess \
the value yourself.
- Where a step looks something up and no later step posts what it found, ask the agent to \
report that back to you in its reply.

You also write the JUDGE SPECIFICATION. You are given the items that need checking, each with \
where its answer must appear. For each one return:
- expected: THE ANSWER ITSELF, in a sentence. Two ways to get this wrong, and both make the item \
useless. Do not write "the text returned by step N" or "the answer to the question above" — a \
grader given that has nothing to compare against. And do not paste the returned value back \
verbatim — say what a correct answer STATES, in your own words, so that a grader can recognise one \
that is worded differently. Where the item shows what the step actually returned, draw the facts \
out of it ("names all three of X, Y and Z"); where the answer comes from outside the workspace, \
give it as best you know it.
- hint: where in the agent's output a grader should look for it.

Respond with ONLY this JSON object:
{"prompt": "<the task text>",
 "judge": [{"id": "<item id, copied exactly>", "expected": "...", "hint": "..."}]}"""

_V2_SYSTEM = """You rewrite a task so that it names nothing, and asks for exactly the same work.

You are given the workspace, the plan the task encodes, the current task text, and — for every \
entity involved — a description that is TRUE OF IT AND OF NOTHING ELSE in that workspace. \
Rewrite the task as coherent connected prose, replacing every identifier with the description \
supplied for that entity.

- Continuous paragraphs. No numbered list, no bullets, no "Step 1:" — if the result still reads \
as a list of instructions, it is not done.
- Use the descriptions given. They were checked against the workspace; anything you invent was \
not, and a reference matching two things makes the task unanswerable.
- Never answer your own reference. No parenthetical, no "i.e.", no appositive that supplies the \
name or id of something you have just described.
- Do not add, drop, merge or reorder an action, and never turn a read into a write.
- Reproduce every repository name and question word for word. The expected answers are keyed to \
them.
- It must read like an ordinary request from a colleague: say what you want and where to report \
back, never why. No mention of steps, tools, plans or rules.

Respond with ONLY this JSON object:
{"prompt": "<the rewritten task>"}"""

_V3_SYSTEM = """You rewrite a task as the request a person would actually have sent.

You are given the workspace, the underlying plan, and a task written as connected prose. Raise \
its level of abstraction: say what you are trying to ACHIEVE and let the steps follow from it.

- No enumeration. No numbered or bulleted steps, and no sentence that reads as "and then".
- Nothing quoted or dictated word for word — except repository names and questions, which must \
survive exactly, because the expected answers are keyed to them.
- Individual steps must stop being individually identifiable. Fold them into the goal.
- Keep every reference resolvable: an agent reading this must still be able to work out which \
things you mean.
- Refer to things the way the list below does, and never by name. A description with the answer \
bolted on — "Alice Rivera (the author of the message about the freeze)" — is worse than either half \
of it alone: it hands back the very step the description existed to create. No parenthetical, no \
"i.e.", no appositive naming what you have just described.
- You are shown the plan so you can check your text still leads to those actions. It is not \
something to reproduce, and none of it should be recognisable as a list.

The test is simple: a colleague reading this should see a normal ask, and an agent following it \
should end up doing the same work.

Respond with ONLY this JSON object:
{"prompt": "<the rewritten task>"}"""


def judge_items(spec: dict, sequence: Sequence, observed: dict[str, str]) -> list[dict]:
    """What a judge has to check, and where each answer has to appear.

    Two things qualify, and only two. A **carry** requirement, where a value edge means one
    step's message has to contain what an earlier step returned — the state diff sees that the
    message exists but never what is in it. And a **read nothing carries**, whose answer has
    nowhere to land but the agent's reply; without that requirement the read is a step no
    component of the reward can see, and the task would silently be asking for something
    unscorable.

    Authored free text is deliberately absent. The author invented it, so checking the agent
    reproduced it word for word measures obedience to phrasing — and v3 removes the phrasing.
    """
    actions = {action.id: action for action in parse_actions(spec)}
    consumed = {
        source
        for step in sequence.steps
        for sources in step.carries.values()
        for source in sources
    }
    items = []
    for step in sequence.steps:
        number = sequence.number(step.key)
        for param, sources in step.carries.items():
            where = " and ".join(f"step {sequence.number(key)}" for key in sources)
            items.append(
                {
                    "id": f"carry:{step.key}:{param}",
                    "step": number,
                    "requirement": f"the {param} of step {number} must carry what {where} returned",
                    "delivered_in": f"the message step {number} posts",
                    "sources": [
                        {
                            "step": sequence.number(key),
                            "action": sequence.step(key).action,
                            "returns": actions[sequence.step(key).action].returns,
                            "returned": observed.get(key),
                        }
                        for key in sources
                    ],
                }
            )
        if step.produces_value and step.key not in consumed:
            items.append(
                {
                    "id": f"report:{step.key}",
                    "step": number,
                    "requirement": (
                        f"step {number} looks something up and no later step posts what it "
                        "found, so the agent must report it back in its own reply"
                    ),
                    "delivered_in": "the agent's final reply",
                    "sources": [
                        {
                            "step": number,
                            "action": step.action,
                            "returns": actions[step.action].returns,
                            "returned": observed.get(step.key),
                        }
                    ],
                }
            )
    return items


def author_v1(
    author: Author,
    spec: dict,
    sequence: Sequence,
    adapter: ChatAdapter,
    seed: ChatState,
    binding: dict[str, str],
    content: dict[str, str],
    observed: dict[str, str],
    context: str,
) -> tuple[str, list[dict], str]:
    """Stage 8. `(prompt, judge spec, the concrete plan text)`."""
    plan = concrete_steps(
        spec,
        sequence,
        describe_symbols(sequence, adapter, seed, binding),
        content,
        observed,
    )
    items = judge_items(spec, sequence, observed)
    request = "\n\n".join(
        [
            context,
            "WORKSPACE\n" + summarise(seed),
            "PLAN (perform in this order)\n" + plan,
            "ITEMS THAT NEED CHECKING\n" + _render_items(items),
        ]
    )

    def complete(reply: dict) -> None:
        _text(reply)
        _merge_judge(items, reply.get("judge") or [])

    reply = author.ask(sequence.task_id, "prompt_v1", _V1_SYSTEM, request, complete)
    return _text(reply), _merge_judge(items, reply.get("judge") or []), plan


def author_v2(
    author: Author,
    spec: dict,
    sequence: Sequence,
    adapter: ChatAdapter,
    seed: ChatState,
    binding: dict[str, str],
    references: dict[str, dict],
    plan: str,
    previous: str,
    context: str,
) -> tuple[str, list[str]]:
    """Stage 9. `(prompt, checks this version did not pass)`."""
    lines = [
        f"  {binding[symbol]} -> {reference['phrase']}"
        for symbol, reference in references.items()
    ]
    forbidden = _forbidden(spec, adapter, seed, binding, references)
    request = "\n\n".join(
        [
            context,
            "WORKSPACE\n" + summarise(seed),
            "PLAN THE TASK MUST STILL ENCODE\n" + plan,
            "HOW TO REFER TO EACH THING INSTEAD OF NAMING IT\n" + "\n".join(lines),
            "THESE STRINGS MUST NOT APPEAR IN YOUR TEXT\n  "
            + ", ".join(sorted(forbidden)),
            "CURRENT TASK TEXT (rewrite this)\n" + previous,
        ]
    )
    reply = author.ask(sequence.task_id, "prompt_v2", _V2_SYSTEM, request, _text)
    prompt = _text(reply)
    return prompt, _complaints(prompt, forbidden)


def author_v3(
    author: Author,
    spec: dict,
    sequence: Sequence,
    adapter: ChatAdapter,
    seed: ChatState,
    binding: dict[str, str],
    references: dict[str, dict],
    plan: str,
    previous: str,
    context: str,
) -> tuple[str, list[str]]:
    """Stage 10. `(prompt, checks this version did not pass)`."""
    lines = [f"  {reference['phrase']}" for reference in references.values()]
    forbidden = _forbidden(spec, adapter, seed, binding, references)
    request = "\n\n".join(
        [
            context,
            "WORKSPACE\n" + summarise(seed),
            "PLAN YOUR TEXT MUST STILL LEAD TO (do not reproduce it)\n" + plan,
            "KEEP REFERRING TO THINGS THIS WAY, AND NEVER BY NAME\n" + "\n".join(lines),
            "THESE STRINGS MUST NOT APPEAR IN YOUR TEXT\n  "
            + ", ".join(sorted(forbidden)),
            "CURRENT TASK TEXT (rewrite this)\n" + previous,
        ]
    )
    reply = author.ask(sequence.task_id, "prompt_v3", _V3_SYSTEM, request, _text)
    prompt = _text(reply)
    return prompt, _complaints(prompt, forbidden)


def describe_symbols(
    sequence: Sequence, adapter: ChatAdapter, seed: ChatState, binding: dict[str, str]
) -> dict[str, str]:
    """Symbol -> a line about the entity behind it. Seed entities are named and described;
    a rollout entity has nothing to describe yet but the step that will bring it into being."""
    described = {}
    for entry in sequence.manifest:
        if entry.origin == "seed":
            entity_id = binding[entry.symbol]
            described[entry.symbol] = (
                f"{entity_id} — {adapter.describe(seed, entity_id)}"
            )
        else:
            number = sequence.number(entry.created_by)
            described[entry.symbol] = f"the {entry.entity_type} step {number} creates"
    return described


def _render_items(items: list[dict]) -> str:
    if not items:
        return "  (none — nothing in this task needs a judge)"
    lines = []
    for item in items:
        lines.append(f"  {item['id']}")
        lines.append(f"      {item['requirement']}")
        lines.append(f"      delivered in: {item['delivered_in']}")
        for source in item["sources"]:
            lines.append(
                f"      step {source['step']} ({source['action']}) returns {source['returns']}"
            )
            if source["returned"] is not None:
                lines.append(
                    f"          it actually returned: {source['returned'][:700]}"
                )
    return "\n".join(lines)


def _merge_judge(items: list[dict], authored: list) -> list[dict]:
    by_id = {
        entry["id"]: entry
        for entry in authored
        if isinstance(entry, dict) and "id" in entry
    }
    merged = []
    for item in items:
        entry = by_id.get(item["id"])
        if entry is None or not str(entry.get("expected", "")).strip():
            raise AuthoringError(
                f'no expected answer for judge item "{item["id"]}"; every item needs an entry '
                "carrying its id verbatim and a non-empty expected"
            )
        merged.append(
            {
                "id": item["id"],
                "requirement": item["requirement"],
                "expected": str(entry["expected"]),
                "hint": str(entry.get("hint") or item["delivered_in"]),
                "delivered_in": item["delivered_in"],
            }
        )
    return merged


def _text(reply: dict) -> str:
    prompt = reply.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise AuthoringError('the reply had no "prompt" string in it')
    return prompt.strip()


def _forbidden(
    spec: dict,
    adapter: ChatAdapter,
    seed: ChatState,
    binding: dict[str, str],
    references: dict[str, dict],
) -> set[str]:
    """Strings a de-scaffolded prompt must not contain.

    Three kinds. Every id in the seed, because naming one hands the agent the resolution step for
    free — the entire difference between v1 and v2. Every action and tool name, because naming one
    turns a request from a colleague back into an instruction to call a function. And, for each
    entity the prompt is supposed to *describe*, whatever would identify it outright: a person's
    display name and handle, a chat's title. That last kind is what stops "Alice Rivera (the author
    of the message about the freeze)" — a description with the answer bolted on.

    Whatever the assigned reference itself says is exempt. Where the chosen mode *is* the name, the
    name is the description and has to survive.
    """
    spoken = {
        str(value)
        for reference in references.values()
        for value in reference["params"].values()
    }
    described = {
        away
        for symbol in references
        for away in adapter.giveaways(seed, binding[symbol])
        if away and away not in spoken
    }
    return (
        {*seed.users, *seed.chats, *(message.id for message in seed.messages)}
        | {action["id"] for action in spec["actions"]}
        | {action["tool"] for action in spec["actions"]}
        | described
    )


def _complaints(prompt: str, forbidden: set[str]) -> list[str]:
    """Checks v2 and v3 are both supposed to pass. Recorded, not enforced — the plan defers an
    automated ambiguity check, and these two are the cheap corner of it."""
    # On a word boundary, not as a substring: user ids are derived from handles, so a plain `in`
    # reports `u_bob` leaked every time `u_bobby` appears and the count stops meaning anything.
    # A boundary match also handles the multi-word entries (a display name, a chat title).
    complaints = [
        f"named {entry!r}"
        for entry in sorted(forbidden)
        if re.search(rf"\b{re.escape(entry)}\b", prompt, re.IGNORECASE)
    ]
    if enumerated := [
        line for line in prompt.splitlines() if re.match(r"\s*(\d+[.)]|[-*•])\s", line)
    ]:
        complaints.append(f"still enumerates {len(enumerated)} step(s)")
    return complaints
