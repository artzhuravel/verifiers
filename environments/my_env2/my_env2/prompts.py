"""Stages 8 to 11 — the same task written four ways, plus the judge specification.

The four versions differ only in how much of the work the prompt does for the agent:

- **v1** numbers the steps and names ids. It is the floor you measure everything else against.
- **v2** is prose, and every id is replaced by the description Stage 4 proved singles it out.
  The agent now has to inspect the environment before it can act at all.
- **v3** asks for the goal. No enumerated steps, nothing that reads like a transcription.
- **v4** is the message a colleague would have typed: actions that exist only to feed each other
  are folded into one request, and no content is dictated word for word.

`(seed, expected)` is identical across all four, so a score difference between two of them is
attributable to how the task was specified and to nothing else.

**The judge specification travels with the prompt.** It is authored alongside v1, which still
states everything explicitly — and then rewritten at every rung, because a judge item written
against v1 speaks v1: step numbers, entity ids, display names, all of which the next rung
removes. An item that still says "look at the message the agent sent to chat c_001 (step 4)" is
describing a task the agent was never given. So each rewrite stage is handed the current items
and must restate each one's `expected` and `hint` in terms of its own text. `id`, `requirement`
and `delivered_in` stay derived and are never authored: **which** items need judging and
**where** each answer has to be delivered are decided in code, because an author free to choose
a destination invents a message the plan does not contain, and the state reward then penalises
an agent for obeying the prompt.

**Descriptions introduce, they do not substitute.** The first version of the rewrite stages told
the model to replace every identifier with the entity's description, and it did so literally:
over twelve tasks, 40 of 81 phrase uses were the same description pasted again, one of them five
times in a single prompt. Worse, a description can depend on something the task itself changes —
"the one conversation you still have not caught up on", in a task whose third step marks that
conversation read — so the second and later uses are not just clumsy but false. Every rewrite
stage now asks for the description once, at first mention, and ordinary anaphora after it, and
`_complaints` counts repeats.
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

_REFER_ONCE = """- A description INTRODUCES a thing. Use it at the first mention only. Every later \
mention refers back the way a person would — "that conversation", "the same thread", "there", \
"them", "it", "the one you just read". Pasting a description a second time is the commonest way \
this rewrite fails: it reads as find-and-replace rather than as writing, and where a description \
depends on something the task itself changes, every use after that change is simply FALSE. Any \
description marked below as one the work invalidates must be used early and never again.
- Never answer your own reference. No parenthetical, no "i.e.", no appositive that supplies the \
name or id of something you have just described."""

_JUDGE_REWRITE = """
You also rewrite the JUDGE ITEMS. Each tells a grader what a correct answer says and where in the \
agent's output to look for it. They were written against the PREVIOUS version of this task, so they \
still speak its language — step numbers, entity ids, names, quoted wording — much of which you are \
removing. Left alone, they describe a task the agent was never given.

For every item, restate `expected` and `hint` so that a grader reading YOUR text can still check \
the same thing:

- `expected` — what a correct answer STATES, in substance. Keep every fact in it. Where the \
previous wording leaned on an id or a step number to say WHICH thing ("the reply to m_004"), say it \
the way your text says it. Never replace it with a pointer: "the answer to the question above" \
leaves a grader nothing to compare against.
- `hint` — where in the agent's output to look, described the way your text describes it.

Do not drop an item, do not merge two, and never change WHAT is required — only how it is said. \
Copy each `id` exactly."""

_REWRITE_OUTPUT = """
Respond with ONLY this JSON object:
{"prompt": "<the rewritten task>",
 "judge": [{"id": "<copied exactly>", "expected": "...", "hint": "..."}]}"""

_V2_SYSTEM = f"""You rewrite a task so that it names nothing, and asks for exactly the same work.

You are given the workspace, the plan the task encodes, the current task text, and — for every \
entity involved — a description that is TRUE OF IT AND OF NOTHING ELSE in that workspace. \
Rewrite the task as coherent connected prose that picks each thing out by description rather than \
by id.

- Continuous paragraphs. No numbered list, no bullets, no "Step 1:" — if the result still reads \
as a list of instructions, it is not done.
- Use the descriptions given. They were checked against the workspace; anything you invent was \
not, and a reference matching two things makes the task unanswerable.
{_REFER_ONCE}
- Do not add, drop, merge or reorder an action, and never turn a read into a write.
- Reproduce every repository name and question word for word. The expected answers are keyed to \
them.
- It must read like an ordinary request from a colleague: say what you want and where to report \
back, never why. No mention of steps, tools, plans or rules.
{_JUDGE_REWRITE}
{_REWRITE_OUTPUT}"""

_V3_SYSTEM = f"""You rewrite a task as the request a person would actually have sent.

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
of it alone: it hands back the very step the description existed to create.
{_REFER_ONCE}
- You are shown the plan so you can check your text still leads to those actions. It is not \
something to reproduce, and none of it should be recognisable as a list.

The test is simple: a colleague reading this should see a normal ask, and an agent following it \
should end up doing the same work.
{_JUDGE_REWRITE}
{_REWRITE_OUTPUT}"""

_V4_SYSTEM = f"""You rewrite a task as the message a colleague would actually have typed.

You are given the workspace, the plan, and a task that already reads as prose. It is still a \
sequence in disguise: every action gets its own clause, in the plan's order, and anything one \
action needs from another is spelled out as a hand-off. Take that apart.

- FOLD. Where one action exists only to feed another, they are ONE request, not two. "Read the \
recent messages there and keep the array they return for later" followed by "post a message whose \
body reproduces the sender and text of each message from that read" is one thing a person would \
ask for: "catch the room up by posting a rundown of who said what". Ask for the outcome; the \
lookups it takes follow from it and do not need saying.
- NO HAND-OFF LANGUAGE. Nothing "returned", "retained", "kept for later use", "from the earlier \
read", "for use in later actions". A person does not narrate their own request as a data flow.
- STOP DICTATING TEXT. Do not quote a message body or a question. Say what it has to get across \
and leave the wording to the agent. Not: ask about 'owner/repo' the question "What is this project \
for, and what's its primary programming language?" — instead: find out what owner/repo is for and \
what it is mostly written in. The one thing that must survive EXACTLY is a repository NAME: which \
repo was asked about is what the expected answer is keyed to.
{_REFER_ONCE}
- Every action in the plan must still be reachable from what you write, and you must not invite \
one the plan does not contain. Folding changes how the work is ASKED FOR, never what the work is.

The test: read it aloud. If it sounds like someone who needs something done, it is right. If it \
sounds like someone reading out a checklist, fold harder.
{_JUDGE_REWRITE}
{_REWRITE_OUTPUT}"""


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


LEVELS = ("1", "2", "3", "4")
"""Every rung a task ships. Level 1 is authored outright; 2, 3 and 4 are each a rewrite of the
one below, and each carries the judge specification forward with it."""

_REWRITE = {
    "2": {
        "stage": "prompt_v2",
        "system": _V2_SYSTEM,
        "plan_label": "PLAN THE TASK MUST STILL ENCODE",
        "reference_label": "HOW TO REFER TO EACH THING INSTEAD OF NAMING IT — each ONCE, at its "
        "first mention, then refer back",
        "show_ids": True,
        "flag_sequencing": False,  # v2 is prose; reading sequentially is allowed here
        "require_verbatim": True,
    },
    "3": {
        "stage": "prompt_v3",
        "system": _V3_SYSTEM,
        "plan_label": "PLAN YOUR TEXT MUST STILL LEAD TO (do not reproduce it)",
        "reference_label": "KEEP REFERRING TO THINGS THIS WAY, AND NEVER BY NAME — each ONCE, "
        "then refer back",
        "show_ids": False,
        "flag_sequencing": True,
        "require_verbatim": True,
    },
    "4": {
        "stage": "prompt_v4",
        "system": _V4_SYSTEM,
        "plan_label": "PLAN YOUR TEXT MUST STILL LEAD TO (do not reproduce it, and do not walk "
        "through it in order)",
        "reference_label": "THE ONLY WAYS TO PICK EACH THING OUT — each ONCE, then refer back",
        "show_ids": False,
        "flag_sequencing": True,
        # L4 may render a description in natural English rather than quoting it, so a zero count is
        # not by itself a fault here. Nothing then verifies the paraphrase still resolves — that is
        # the deferred ambiguity check, and this is where it would bite first.
        "require_verbatim": False,
    },
}


def rewrite_prompt(
    author: Author,
    level: str,
    spec: dict,
    sequence: Sequence,
    adapter: ChatAdapter,
    seed: ChatState,
    binding: dict[str, str],
    references: dict[str, dict],
    plan: str,
    previous: str,
    judge: list[dict],
    stale: set[str],
    context: str,
) -> tuple[str, list[dict], list[str]]:
    """One rung of the ladder. `(prompt, the judge spec restated for it, complaints)`.

    Levels 2, 3 and 4 differ only in their system prompt and three labels, so they share this.
    Each is handed the rung below's text *and* the rung below's judge items, and must restate both
    — a judge item is part of a task's specification, and a specification that still names steps
    and ids describes a task the agent was never given.

    `stale` names references the task's own work invalidates. They are flagged rather than
    forbidden: the fix is to introduce such a thing before the work that breaks it and refer back
    afterwards, which is what the prompt asks for anyway.
    """
    setting = _REWRITE[level]
    lines = []
    for symbol, reference in references.items():
        prefix = f"  {binding[symbol]} -> " if setting["show_ids"] else "  "
        note = (
            "\n        [THE WORK ITSELF MAKES THIS FALSE — true at the start, not at the end. "
            "Use it early, once, then refer back.]"
            if symbol in stale
            else ""
        )
        lines.append(f"{prefix}{reference['phrase']}{note}")

    forbidden = _forbidden(spec, adapter, seed, binding, references)
    request = "\n\n".join(
        [
            context,
            "WORKSPACE\n" + summarise(seed),
            f"{setting['plan_label']}\n" + plan,
            f"{setting['reference_label']}\n" + "\n".join(lines),
            "THESE STRINGS MUST NOT APPEAR IN YOUR TEXT\n  " + ", ".join(sorted(forbidden)),
            "JUDGE ITEMS — REWRITE EACH ONE'S expected AND hint FOR YOUR TEXT\n"
            + _render_for_rewrite(judge),
            "CURRENT TASK TEXT (rewrite this)\n" + previous,
        ]
    )

    def complete(reply: dict) -> None:
        _text(reply)
        _rewrite_judge(judge, reply.get("judge") or [])

    reply = author.ask(sequence.task_id, setting["stage"], setting["system"], request, complete)
    prompt = _text(reply)
    restated = _rewrite_judge(judge, reply.get("judge") or [])
    complaints = _complaints(
        prompt,
        forbidden,
        [r["phrase"] for r in references.values()],
        flag_sequencing=setting["flag_sequencing"],
        require_verbatim=setting["require_verbatim"],
    )
    # The same test, over the restated items. A `hint` still reading "the message the agent sent to
    # chat c_001 (step 4)" is not a leak to the agent — it never sees the judge — but it points a
    # grader at a task this rung does not describe, which is the drift the restating exists to fix.
    complaints += [f"judge item {item['id']}: {leak}" for item in restated
                   for leak in _judge_leaks(item, forbidden)]
    return prompt, restated, complaints


def stale_references(
    adapter: ChatAdapter,
    expected: ChatState,
    binding: dict[str, str],
    references: dict[str, dict],
) -> set[str]:
    """Symbols whose description stops picking them out once the task has been carried out.

    Uniqueness is proved against the seed, which is where the agent starts reading — but a
    description can depend on a property the task's own steps destroy. The measured case is a chat
    referred to as the only one with anything unread, in a task that marks it read: the prompt
    then goes on to name it that way twice more, and both are false. Re-resolving against the end
    state is env-agnostic and costs nothing, since `expected` already exists by this point.
    """
    return {
        symbol
        for symbol, reference in references.items()
        if adapter.resolve(expected, reference["mode"], reference["params"]) != [binding[symbol]]
    }


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


def _render_for_rewrite(items: list[dict]) -> str:
    """The judge spec as a rewrite stage is shown it: what is fixed, and what it must restate."""
    if not items:
        return "  (none — nothing in this task needs a judge, so there is nothing to restate)"
    lines = []
    for item in items:
        lines += [
            f"  {item['id']}",
            f"      requirement (FIXED, do not change): {item['requirement']}",
            f"      must be delivered in (FIXED): {item['delivered_in']}",
            f"      expected — RESTATE FOR YOUR TEXT: {item['expected']}",
            f"      hint     — RESTATE FOR YOUR TEXT: {item['hint']}",
        ]
    return "\n".join(lines)


def _rewrite_judge(items: list[dict], authored: list) -> list[dict]:
    """The rung below's items, with `expected` and `hint` restated for the rung above.

    `id`, `requirement` and `delivered_in` are derived and carried through untouched — letting an
    author restate the requirement invites it to weaken one, and letting it choose the delivery
    target invents a message the plan does not contain.
    """
    by_id = {
        entry["id"]: entry for entry in authored if isinstance(entry, dict) and "id" in entry
    }
    merged = []
    for item in items:
        entry = by_id.get(item["id"])
        if entry is None or not str(entry.get("expected", "")).strip():
            raise AuthoringError(
                f'judge item "{item["id"]}" was not restated; every item needs an entry carrying '
                "its id verbatim and a non-empty expected"
            )
        merged.append(
            {
                **item,
                "expected": str(entry["expected"]),
                "hint": str(entry.get("hint") or item["hint"]),
            }
        )
    return merged


def _judge_leaks(item: dict, forbidden: set[str]) -> list[str]:
    """Whether a restated item still speaks the rung below's language.

    Only `hint` is held to the forbidden list, and that distinction is the whole point. `hint` says
    *where to look*, so an id or a tool name in it points a grader at a task the rung does not
    describe. `expected` is the **answer key**: when the work is to find someone's handle and pass
    it on, a correct answer contains that handle, and an item forbidden from stating it would be
    inert. Applying one rule to both flagged three items in t8 whose expected answers were exactly
    right — "includes Cara's handle @cara" — which is the check being wrong, not the author.

    A step number is a fault in either field: nothing about the obligation needs one, and a grader
    reading "step 4" against a prompt with no steps has nothing to find.

    `requirement` is exempt entirely: it is derived, states the obligation in plan terms, and is
    identical at every rung by design.
    """
    leaks = [
        f"the hint still names {entry!r}"
        for entry in sorted(forbidden)
        if re.search(rf"\b{re.escape(entry)}\b", item["hint"], re.IGNORECASE)
    ]
    if re.search(r"(?i)\bsteps?\s+\d", f"{item['expected']}\n{item['hint']}"):
        leaks.append("still refers to a step by number")
    return leaks


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


def _complaints(
    prompt: str,
    forbidden: set[str],
    phrases: list[str] | tuple[str, ...] = (),
    *,
    flag_sequencing: bool = False,
    require_verbatim: bool = False,
) -> list[str]:
    """Checks every de-scaffolded rung is supposed to pass. Recorded, not enforced — the plan
    defers an automated ambiguity check, and these are the cheap corner of it."""
    # On a word boundary, not as a substring: user ids are derived from handles, so a plain `in`
    # reports `u_bob` leaked every time `u_bobby` appears and the count stops meaning anything.
    # A boundary match also handles the multi-word entries (a display name, a chat title).
    complaints = [
        f"named {entry!r}"
        for entry in sorted(forbidden)
        if re.search(rf"\b{re.escape(entry)}\b", prompt, re.IGNORECASE)
    ]
    # A description is for introducing a thing once. Repeating it verbatim is what a
    # find-and-replace produces rather than what writing produces, and it was the single most
    # common defect in these rewrites — 40 of 81 phrase uses over twelve tasks. Using it zero times
    # is the opposite failure and the worse one: a reference the prompt never establishes leaves the
    # task unanswerable rather than merely clumsy.
    for phrase in phrases:
        count = prompt.count(phrase)
        if count > 1:
            complaints.append(
                f"pasted the description {phrase!r} {count} times; introduce a thing once, "
                "then refer back to it"
            )
        elif count == 0 and require_verbatim:
            complaints.append(
                f"never uses the description {phrase!r}; the thing it picks out is either "
                "unreferenced or referred to some other way, which nothing has checked resolves"
            )
    if enumerated := [
        line for line in prompt.splitlines() if re.match(r"\s*(\d+[.)]|[-*•])\s", line)
    ]:
        complaints.append(f"still enumerates {len(enumerated)} step(s)")
    # Only the goal-level rungs. v2 is prose and is allowed to read sequentially; v3 and v4 forbid
    # "and then" chaining, and nothing used to check it — 6 of 12 v3 prompts chained their steps
    # with `; ` or ` then ` while passing every other check.
    if flag_sequencing and (joins := len(re.findall(r"(?i)\b(?:and )?then\b|;\s", prompt))):
        complaints.append(f"{joins} sequencing connective(s) — reads as a list in prose clothing")
    return complaints
