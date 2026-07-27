"""Author natural-language tasks from generated scaffolds — a one-time, LLM-backed step.

Runs the deterministic `generate` for N scaffolds and turns each into a task prompt plus
concretized open-ended DeepWiki items (question + gold answer + a hint for where the
judge should look). It is nondeterministic and LLM-costed, so run it once and treat the
JSONL as the frozen, reusable artifact.

Prompts are authored at an **ambiguity ladder** of increasing difficulty. L1 is what the
authoring pass emits directly (explicit, often naming raw ids — the easy floor you
measure against). Each higher rung is a further rewrite of the rung below, layering on
one more class of indirection:

    L1 explicit  ->  L2 descriptive / de-scaffolded  ->  L3 relational / temporal
                 ->  L4 conditional                 ->  L5 noisy

Noise goes last on purpose: it perturbs the surface of whatever the rungs below produced,
so applying it earlier would just give the later rewrites typos to tidy up.

(An anaphoric rung was tried and removed: these plans touch a different entity at almost
every step, so there is nothing for a pronoun to bind to, and the rewriter reliably
substituted an invented index or plain compression instead. Reinstating it needs the
generator to reuse entities across steps.)

One file per level, and every level holds the SAME tasks: for a given `idx` the seed,
expected state, steps and golds are identical across files and only `prompt` differs. A
score difference between two levels is therefore attributable to the phrasing rather
than to authoring noise — which is the whole point of the ladder. To keep that true, a
task that fails at any rung is dropped from every file.

Each rewrite is re-anchored to the original plan and app state, not just handed the
previous prompt: three chained rewrites otherwise accumulate semantic drift with nothing
to correct against.

    uv run python -m my_env.author --num 12 --levels 4
    (needs OPENROUTER_BASE_URL and OPENROUTER_API_KEY in the environment)
"""

import argparse
import json
import os
from pathlib import Path

from openai import OpenAI

from my_env.adapter import ChatAdapter
from my_env.generate import generate

_SPEC = json.loads((Path(__file__).parent / "action_spec.json").read_text())

_SYSTEM = """You write a single natural-language task for an agent that operates a small \
chat app, and for some steps a DeepWiki tool that answers questions about GitHub repos.

You are given the app's current state and an ordered plan of the exact actions the agent \
should perform. Rewrite the plan as ONE coherent task at MODERATE ambiguity:
- Refer to chats/messages/users by natural descriptions ("the launch channel", "the \
message Wei replied to", "Priya on the design side"), NOT by raw ids like c_001 or m_003.
- Keep the intended actions UNIQUELY recoverable — harder to parse, not underspecified. A \
careful agent should be able to reconstruct exactly the listed actions, in order.
- BEWARE: display names and topics COLLIDE in this workspace. Several people share a first \
name (distinguished only by their @handle), and the same subject is discussed in more than \
one chat. A bare first name ("ask Alex") or a bare topic ("the chat about the launch") is \
therefore NOT a unique reference. Disambiguate with a handle, a chat, a thread position, or \
some other fact that is true of exactly one entity — then double-check it really is unique.
- Cover every step, in order.
- Describe each step as the operation its own tool performs, and NEVER upgrade a read into \
a write. `chat_read_messages` means *read* a chat's messages — it does NOT mean "mark the \
chat as read" (that is `chat_mark_read`, a different action with a lasting effect). \
Likewise `chat_get_user` only looks a person up. If the plan does not contain a write, the \
prompt must not ask for one.

For each [open-ended] DeepWiki step, YOU choose a real GitHub repo and a specific question \
(language, authors, license, purpose, stars — anything) and weave the request naturally \
into the task. IMPORTANT: the agent sees ONLY your `prompt` text — it never sees the list \
below — so embed the full repo name and the exact question directly in the prompt. Never \
write "see the open-ended step below" or refer to a separate list. Then record for it:
- question: the exact question you embedded in the prompt,
- ground_truth: the correct answer (your best knowledge),
- judge_hint: where in the agent's output the answer should appear — it must name the \
same place the DELIVERY RULES below assign to that step.

DELIVERY RULES (breaking these makes the task unscorable):
The ACTION PLAN is the complete and exact set of actions the agent may perform. NEVER \
invent an action that is not in it. In particular, do NOT ask the agent to send, post or \
reply with anything unless the plan already contains that write step — an unplanned \
message is an unexpected change to the app, and the agent gets penalised for obeying you.
For every open-ended step you are told below exactly where its answer must go: either \
into a specific later write step that already exists in the plan, or — when no write step \
follows it — in the agent's reply to you. Follow that assignment exactly.

These rules are for YOU. They are not text to reproduce. The prompt you write must read \
like an ordinary request from a colleague: ask for what you want and say where to report \
back, never why. Do not justify a destination ("because no write step follows"), do not \
append a summary of what the agent may or may not do ("perform only these operations; make \
no other sends"), and do not mention rules, plans, steps, tools or scoring. Just say e.g. \
"...and let me know what you find" or "...and put that in the message to the design \
channel", then stop.

Respond with ONLY a JSON object, no prose or code fences:
{"prompt": "<the task text>", "open_ended": [{"question": "...", "ground_truth": "...", "judge_hint": "..."}]}
Use an empty list if there are no open-ended steps."""


# The ambiguity ladder. L1 is the authoring pass's own output; every rung above it is a
# rewrite of the rung below that adds one more class of indirection while keeping the
# requested actions identical.
_LEVELS: dict[int, tuple[str, str]] = {
    2: (
        "descriptive / de-scaffolded",
        "Strip the scaffolding (invariant 6) and say what to do, not which function to "
        "call. Write it as flowing prose a colleague would actually send. Then stop NAMING "
        "things: never call a person by their display name or @handle, and never call an "
        "existing chat by its title. Describe each one instead — not 'the launch-eng chat' "
        "but 'the engineering channel where the migration failures were posted'; not "
        "'Priya @praman' but 'the designer who put the new onboarding flow up for review'. "
        "(The names of chats the task CREATES are part of the request and must stay.)",
    ),
    3: (
        "relational / temporal",
        "Replace descriptions with RELATIONSHIPS and ORDERING, so the agent has to inspect "
        "the app to resolve them. Identify a message by its place in a thread ('the reply "
        "that pushed back on the stale-counter idea'), a person by what they did ('whoever "
        "disagreed with the teammate who wanted to slip a week'), a chat by its content or "
        "recency ('the one where the espresso machine came up'). Prefer 'the oldest unread "
        "...' / 'her most recent message' over anything that could be looked up statically.",
    ),
    4: (
        "conditional",
        "Put SOME of the requests behind a condition the agent must evaluate against the "
        "app before it can know what to do — 'if nobody has reacted to that yet, ...', "
        "'unless she already replied in that thread, ...'. Two rules make this safe. "
        "FIRST: the condition must be decidable purely from the app state you were shown, "
        "and it must come out so that the branch containing the REAL requested action is "
        "the one that fires — check the state and get this right, because a condition that "
        "resolves the other way silently destroys the task. SECOND: the branch that does "
        "not fire must describe something plausible that the agent will therefore correctly "
        "NOT do. Leave the remaining requests unconditional; conditioning everything reads "
        "as a puzzle, not a message from a colleague.",
    ),
    5: (
        "noisy",
        "Keep the wording as it is and introduce 2-5 realistic slips of the kind someone "
        "typing quickly makes: transposed letters, a doubled or dropped character, a missing "
        "apostrophe, 'teh', a lowercase sentence start, a comma splice. Spread them through "
        "the prose. NEVER put a slip inside anything quoted, inside a repository name, or "
        "inside an identifier — those are copied exactly (invariant 2). The reader must "
        "still be able to work out precisely what is being asked; you are adding sloppiness, "
        "not doubt.",
    ),
}

_REFINE_SYSTEM = """You rewrite a task prompt for an agent that operates a chat app and a \
DeepWiki tool, making it HARDER TO PARSE without changing one thing about what it asks for.

You are given the app state, the exact action plan the prompt encodes, where each \
open-ended answer must be delivered, and the current prompt. Rewrite the prompt applying \
this layer of difficulty:

  {label} — {operators}

Keep every layer already present in the current prompt; you are adding to it, not \
replacing it.

INVARIANTS — breaking any of these silently destroys the task:
1. An agent that follows your prompt correctly must end up performing exactly the actions \
in the plan, in the same order — never add, drop, merge or reorder one, and never turn a \
read into a write. If the plan has no write, a correct reading must not produce one. (A \
conditional may DESCRIBE an alternative the agent will correctly decide against; what \
matters is what actually gets done.)
2. Every GitHub repo name and DeepWiki question must survive WORD FOR WORD, character for \
character, with nothing appended, prepended or clarified. The expected answers are keyed to \
them; touching one invalidates it. Copy each question across exactly as it appears.
3. Each open-ended answer must still be delivered exactly where the delivery list says — \
the same target message, or the agent's final reply.
4. Every reference must still resolve to EXACTLY ONE entity. Harder to work out is the \
goal; genuinely ambiguous is a bug. Remember that display names and topics collide in this \
workspace, so check each reference really is unique before you use it.
5. The reader must experience an ordinary work request from a colleague — nothing that \
reveals it was constructed. Say what you want done and where to report back, never why. No \
mention of difficulty, ambiguity, rules, steps, plans, tools, or what is or isn't checked; \
no closing summary of what is and isn't permitted. Explaining a constraint is as bad as \
breaking one.
6. Scaffolding, once gone, stays gone. Whatever layer you are adding, the result must \
still contain NO numbered or bulleted steps, NO tool names, and NO raw entity ids like \
c_001, m_003 or u_alex_chen. Write continuous prose. The ONLY ids you may keep are the \
deliberately nonexistent ones the task asks the agent to try anyway (u_missing, m_missing, \
c_missing) — reproduce those exactly. If precision tempts you back toward a numbered list \
or an id, find a sharper description instead.
7. A description must make the reader do the work of identifying the thing. So never \
answer your own reference: no parenthetical, appositive or "i.e." that supplies the name, \
handle or id of something you have just described ("the person who posted X (that's \
Hana)"). And never build an index to point back into — no list of quoted messages, labels \
or reference keys collected anywhere in the prompt, and no referring to anything by its \
position in such a list. If a reference is not precise enough to stand alone, make the \
description sharper; do not annotate it.

Respond with ONLY a JSON object, no prose or code fences:
{{"prompt": "<the rewritten prompt>"}}"""


def _describe(step: dict) -> str:
    if step.get("open_ended"):
        return f"[open-ended] {step['tool']}: you choose the repo + question, and supply the gold answer + judge hint"
    desc = f"{step['tool']}({json.dumps(step['args'])})"
    if step["kind"] == "invalid":
        desc += "  — targets a nonexistent entity; include it as a normal instruction (the agent will attempt it and it will fail)"
    return desc


_DELIVERY_TOOLS = ("chat_send_message", "chat_reply_to")


def _delivery_rules(steps: list[dict]) -> str:
    """Where each open-ended answer must be delivered, decided from the plan rather than
    left to the author. An answer routed into a message the plan does not contain is an
    unexpected state change, and the state-diff reward then penalises an agent for doing
    exactly what the prompt told it to."""
    lines = []
    for i, step in enumerate(steps):
        if not step.get("open_ended"):
            continue
        target = next(
            (
                (number, later)
                for number, later in enumerate(steps[i + 1 :], start=i + 2)
                if later["tool"] in _DELIVERY_TOOLS and not later["expect_error"]
            ),
            None,
        )
        if target is None:
            lines.append(
                f"  - step {i + 1} ({step['tool']}): no write step follows it, so the agent "
                "must report this answer back to you in its own reply. Ask for it the way a "
                "colleague would ('let me know what you find'); never have it posted anywhere "
                "in the app."
            )
        else:
            number, later = target
            lines.append(
                f"  - step {i + 1} ({step['tool']}): its answer belongs in step {number}, the "
                f"{later['tool']} the plan already contains — have the agent write the answer "
                "as that message. (The placeholder text shown for that step is arbitrary; "
                "replace it with the answer.)"
            )
    return "\n".join(lines)


def _who(seed, user_id: str) -> str:
    user = seed.users.get(user_id)
    return f"{user.name} @{user.handle}" if user else user_id


def _render_plan(seed, timeline) -> str:
    lines = [f"APP STATE (you act as {seed.users['u_me'].name}, id u_me):"]
    lines.append("Users:")
    for uid, user in seed.users.items():
        lines.append(f"  {user.name} @{user.handle} ({uid})")
    for cid, chat in seed.chats.items():
        kind = "DM" if chat.kind == "dm" else "group"
        members = ", ".join(_who(seed, m) for m in chat.member_ids)
        lines.append(f"\n{kind} '{chat.name or cid}' ({cid}) — members: {members}")
        for message in (m for m in seed.messages if m.chat_id == cid):
            marks = []
            if message.reply_to:
                marks.append(f"reply to {message.reply_to}")
            if seed.me not in message.read_by:
                marks.append("unread by you")
            if message.reactions:
                marks.append(
                    "reacted " + " ".join(f"{e}x{len(u)}" for e, u in message.reactions.items())
                )
            suffix = f"  ({'; '.join(marks)})" if marks else ""
            lines.append(
                f"  {message.id} [{_who(seed, message.sender_id)}]: {message.text}{suffix}"
            )
    lines.append("\nACTION PLAN (perform in order):")
    steps = [step for group in timeline for step in group]
    for number, step in enumerate(steps, start=1):
        lines.append(f"  {number}. {_describe(step)}")
    if rules := _delivery_rules(steps):
        lines.append("\nWHERE EACH OPEN-ENDED ANSWER MUST BE DELIVERED:")
        lines.append(rules)
    return "\n".join(lines)


def _parse(text: str) -> dict:
    # Tolerate stray prose / code fences: take the outermost JSON object. `strict=False`
    # allows raw newlines inside strings — models routinely emit them in a long `prompt`,
    # and rejecting the whole response over one is not worth it.
    start, end = text.find("{"), text.rfind("}")
    data = json.loads(text[start : end + 1], strict=False)
    prompt = data["prompt"]
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("authoring response carried no prompt text")
    return {"prompt": prompt, "open_ended": data.get("open_ended", [])}


def _complete(client, model: str, system: str, user: str) -> dict:
    response = client.chat.completions.create(
        model=model,
        temperature=0.7,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return _parse(response.choices[0].message.content or "")


def _refine_request(plan: str, open_ended: list[dict], prompt: str) -> str:
    """The rewriter's user message. It gets the ground-truth plan every time rather than
    only the previous prompt, so three chained rewrites re-anchor to the plan instead of
    compounding each other's drift."""
    parts = [plan]
    if open_ended:
        parts.append(
            "\nTHESE QUESTIONS ARE LOAD-BEARING — reproduce each repo name and question "
            "word for word; the expected answers are keyed to them:"
        )
        parts.extend(f"  - {item['question']}" for item in open_ended)
    parts.append("\nCURRENT PROMPT (rewrite this):\n" + prompt)
    return "\n".join(parts)


def _attempt(what: str, idx: int, call) -> dict | None:
    """Run an LLM step, retrying once. Returns None if it failed twice — neither a
    malformed reply nor a transient upstream error should discard a whole LLM-costed
    batch, so this catches broadly and prints the reason rather than raising."""
    for attempt in range(2):
        try:
            return call()
        except Exception as error:  # noqa: BLE001 - offline batch tool; keep going
            print(f"idx {idx}: {what} failed ({type(error).__name__}: {error}); "
                  f"{'retrying' if attempt == 0 else 'dropping task'}")
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num", type=int, default=5)
    parser.add_argument("--out-dir", default=str(Path(__file__).parent))
    parser.add_argument("--levels", type=int, default=max(_LEVELS),
                        help=f"highest ambiguity rung to author (1..{max(_LEVELS)})")
    parser.add_argument("--model", default="openai/gpt-5-mini")
    parser.add_argument("--timesteps", type=int, default=3)
    parser.add_argument("--max-actions", type=int, default=3)
    parser.add_argument("--p-invalid", type=float, default=0.2)
    parser.add_argument("--p-open", type=float, default=0.3)
    args = parser.parse_args()

    if not 1 <= args.levels <= max(_LEVELS):
        raise SystemExit(f"--levels must be between 1 and {max(_LEVELS)}")
    base_url, api_key = os.environ.get("OPENROUTER_BASE_URL"), os.environ.get("OPENROUTER_API_KEY")
    if not base_url or not api_key:
        raise SystemExit("set OPENROUTER_BASE_URL and OPENROUTER_API_KEY in the environment")
    client = OpenAI(base_url=base_url, api_key=api_key)

    adapter = ChatAdapter()
    action_ids = [a["id"] for a in _SPEC["actions"]]
    levels = range(1, args.levels + 1)

    by_level: dict[int, list[dict]] = {level: [] for level in levels}
    dropped = []
    for idx in range(args.num):
        seed, expected, timeline = generate(
            _SPEC, adapter, action_ids, args.timesteps, args.max_actions, args.p_invalid, args.p_open, idx
        )
        plan = _render_plan(seed, timeline)

        authored = _attempt("authoring", idx, lambda: _complete(client, args.model, _SYSTEM, plan))
        if authored is None:
            dropped.append(idx)
            continue

        # Each rung rewrites the one below it; a failure anywhere drops the task from
        # every file, so all levels keep an identical task set and stay comparable.
        prompts = {1: authored["prompt"]}
        for level in levels:
            if level == 1:
                continue
            label, operators = _LEVELS[level]
            system = _REFINE_SYSTEM.format(label=label, operators=operators)
            request = _refine_request(plan, authored["open_ended"], prompts[level - 1])
            refined = _attempt(
                f"L{level} rewrite", idx,
                lambda system=system, request=request: _complete(client, args.model, system, request),
            )
            if refined is None:
                break
            prompts[level] = refined["prompt"]
        if len(prompts) != len(by_level):
            dropped.append(idx)
            continue

        for level, prompt in prompts.items():
            by_level[level].append(
                {
                    "idx": idx,
                    "level": level,
                    "seed": seed.model_dump(),
                    "expected": expected.model_dump(),
                    "steps": [step for group in timeline for step in group],
                    "prompt": prompt,
                    "open_ended": authored["open_ended"],
                }
            )
        print(f"authored idx {idx}: {len(authored['open_ended'])} open item(s), "
              f"L1-L{args.levels} ({', '.join(str(len(p)) for p in prompts.values())} chars)")

    if not any(by_level.values()):
        raise SystemExit("no tasks were authored; nothing written")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for level, rows in by_level.items():
        path = out_dir / f"authored_tasks_l{level}.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        print(f"wrote {path} ({len(rows)} tasks)")
    if dropped:
        print(f"dropped from every level: {dropped}")


if __name__ == "__main__":
    main()
