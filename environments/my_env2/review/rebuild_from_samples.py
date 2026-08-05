"""Rebuild every stage's artifact from an already-authored task file, without a model.

`run_review.py` runs the pipeline live and needs an API key. This needs nothing: every authoring
prompt in this pipeline is a pure function of things a `TaskRecord` already stores, so the
prompts that produced a shipped task can be reconstructed from the task itself.

    uv run --with-editable environments/my_env2 \
        python environments/my_env2/review/rebuild_from_samples.py

What is exact and what is not:

- **Exact** — stages 2, 3, 7, 8, 9 and 10. Their inputs (the sequence, the shipped seed, the
  authored content, the observed reads, the previous prompt) are all in the record, so the
  reconstructed prompt is byte-for-byte what the model received.
- **Format-faithful, different world** — stages 4 and 5. Both were run against the *core* world,
  before padding, and only the padded world ships. The prompt is rebuilt in the right shape
  against the shipped seed instead, so the block layout is real and the workspace inside it is
  the later one. Every such file says so at the top.
- **Real** — every result: the seed, the chosen reference modes, the replay, the content, the
  three prompts and the judge specification are the shipped artifacts, not reconstructions.

The sequence is regenerated from `idx` and checked against the stored steps, so a spec or config
change since the file was authored is caught rather than silently papered over.
"""

import argparse
import json
import random
import sys
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from my_env2.adapter import ChatAdapter  # noqa: E402
from my_env2.authoring import (  # noqa: E402
    _CONTENT_SYSTEM,
    _ENTITIES_SYSTEM,
    _POPULATE_SYSTEM,
    _REFERENCES_SYSTEM,
)
from my_env2.pipeline import DEFAULT_CONFIGS, SPEC_PATH  # noqa: E402
from my_env2.prompts import (  # noqa: E402
    _REWRITE,
    _V1_SYSTEM,
    _forbidden,
    _render_for_rewrite,
    _render_items,
    describe_symbols,
    judge_items,
    stale_references,
)
from my_env2.render import (  # noqa: E402
    concrete_steps,
    manifest_brief,
    shared_context,
    symbolic_steps,
)
from my_env2.replay import replay  # noqa: E402
from my_env2.seed import (  # noqa: E402
    DraftChat,
    DraftMessage,
    DraftUser,
    WorldDraft,
    summarise,
    summarise_draft,
)
from my_env2.spec import reference_modes  # noqa: E402
from my_env2.state import ChatState  # noqa: E402
from my_env2.symbolic import generate_sequence  # noqa: E402

from run_review import (  # noqa: E402
    dump_json,
    render_judge_prompt,
    render_ladder,
    render_references,
    render_replay,
    render_sequence,
    write,
)

EXACT = "This is EXACTLY the prompt the authoring model received. Every input to it is stored\nin the task record, so it is a reconstruction only in the sense that it was rebuilt rather\nthan logged."

APPROX = """NOTE ON FIDELITY — read this before trusting the WORKSPACE block below.

This stage ran against the CORE world, before Stage 5 padded it, and only the padded world is
shipped in the task record. The prompt below is therefore rebuilt in the right shape, with the
right blocks in the right order, but the workspace inside it is the LATER one: it contains
filler that was not present when the model actually saw this. The instructions, the block
structure and the derived lines are real; the world is a stand-in.
"""


DRIFTED = """NOTE ON FIDELITY — the instruction below is CURRENT; the reply below is HISTORICAL.

These twelve tasks are the evidence that made the rewrite stages change. The system prompt shown
here is the one now in the code — it asks for a description to be used once and referred back to
afterwards, and it asks for the judge specification to be restated. The task text shown as the
reply was produced by the PREVIOUS version of this stage, which asked for per-occurrence
substitution and left the judge items alone. Reading the two together is the before-and-after.
"""

UNBUILT = """NO REPLY EXISTS FOR THIS LEVEL.

This rung was added after these twelve tasks were authored, so the task file has no text for it.
The prompt below is what the stage now sends; producing the text needs a live authoring run.
"""


def _judge_at(row: dict, level: str) -> list[dict]:
    """This row's judge items for a level, tolerating the flat pre-per-level schema."""
    judge = row.get("judge") or []
    if isinstance(judge, dict):
        return judge.get(level) or judge.get("1") or []
    return judge


def prompt_file(title: str, note: str, system: str, user: str, reply: str | None) -> str:
    blocks = [
        f"# {title}",
        "",
        note,
        "",
        "-" * 96,
        "-- SYSTEM PROMPT",
        "-" * 96,
        system,
        "",
        "-" * 96,
        "-- USER PROMPT",
        "-" * 96,
        user,
    ]
    if reply is not None:
        blocks += ["", "-" * 96, "-- WHAT THE MODEL RETURNED (the shipped artifact)", "-" * 96, reply]
    return "\n".join(blocks)


def draft_from_state(state: ChatState) -> WorldDraft:
    """A state back into the draft vocabulary Stage 5 speaks (`u1`, `c2`, `m3`).

    Stage 5 is the one call shown the world in local keys rather than real ids, because it has to
    be able to add a message to an existing conversation. Rebuilding that view is what lets its
    prompt be shown at all.
    """
    users, chats, messages = [], [], []
    keys: dict[str, str] = {}
    for number, user in enumerate((u for u in state.users.values() if u.id != state.me), 1):
        keys[user.id] = f"u{number}"
        users.append(DraftUser(ref=f"u{number}", name=user.name, handle=user.handle))
    for number, chat in enumerate(state.chats.values(), 1):
        keys[chat.id] = f"c{number}"
        chats.append(
            DraftChat(
                ref=f"c{number}",
                name=chat.name,
                members=[keys[m] for m in chat.member_ids if m in keys],
            )
        )
    for number, message in enumerate(sorted(state.messages, key=lambda m: m.ts), 1):
        keys[message.id] = f"m{number}"
        reactors = [keys[u] for users_ in message.reactions.values() for u in users_ if u in keys]
        messages.append(
            DraftMessage(
                ref=f"m{number}",
                chat=keys.get(message.chat_id, message.chat_id),
                sender=keys.get(message.sender_id, "actor"),
                text=message.text,
                order=message.ts,
                reply_to=keys.get(message.reply_to) if message.reply_to else None,
                read_by_actor=state.me in message.read_by,
                reactors=reactors,
                reaction_emoji=next(iter(message.reactions), ":+1:"),
            )
        )
    return WorldDraft(topic="", actor_name=state.users[state.me].name,
                      users=users, chats=chats, messages=messages)


def rebuild(spec: dict, row: dict, adapter: ChatAdapter, out: Path) -> dict:
    idx, task_id = row["idx"], row["task_id"]
    directory = out / task_id
    step = lambda name: directory / name  # noqa: E731

    sequence = generate_sequence(spec, random.Random(idx), DEFAULT_CONFIGS, task_id=task_id)
    regenerated = [asdict(s) for s in sequence.steps]
    if regenerated != row["steps"]:
        raise RuntimeError(
            f"{task_id}: regenerating the sequence from idx {idx} no longer reproduces the stored "
            "steps — the spec or DEFAULT_CONFIGS changed since this task was authored, so the "
            "prompts below could not be rebuilt faithfully"
        )

    seed = ChatState.model_validate(row["seed"])
    binding = row["binding"]
    references = row["references"]
    content = row["content"]
    observed = row["observed"]
    context = shared_context(spec, sequence)

    # -- stage 1
    write(step("01_sequence.txt"), render_sequence(spec, sequence, idx))

    # -- stage 2
    write(
        step("02_shared_context.txt"),
        "Stage 2. Built once and prepended to EVERY authoring call below, so all seven decide\n"
        "against the same account of what the environment means. Every word of it comes from the\n"
        "spec — an action's description, a param's description, an entity type's description, an\n"
        "action's `returns`. Nothing in the renderer knows this is a chat app.\n\n" + context,
    )

    # -- stage 3
    world_user = "\n\n".join([
        context,
        "PLAN THE AGENT WILL BE ASKED TO CARRY OUT\n" + symbolic_steps(spec, sequence),
        "PLACEHOLDERS THAT MUST ALREADY EXIST\n" + manifest_brief(sequence),
        "BIND EXACTLY THESE, ONE EACH, AND NOTHING ELSE\n  "
        + ", ".join(f"{e.symbol} (a {e.entity_type})" for e in sequence.manifest if e.origin == "seed"),
    ])
    write(step("03_world.prompt.txt"),
          prompt_file("Stage 3 — invent the core world", EXACT, _ENTITIES_SYSTEM, world_user,
                      "The draft itself is not stored — only the state built from it. See "
                      "03_world.result.txt for what it became."))
    write(
        step("03_world.result.txt"),
        f"Stage 3 result (as shipped, after Stage 5 padding).\n\ntopic: {row['topic']}\n\n"
        + summarise(seed)
        + "\n\nPLACEHOLDERS BOUND\n"
        + "\n".join(
            f"  {s:22} -> {i:12} ({sequence.entry(s).origin})" for s, i in binding.items()
        ),
    )

    # -- stage 4
    modes = reference_modes(spec)
    lines = []
    for entry in (e for e in sequence.manifest if e.origin == "seed"):
        target = binding[entry.symbol]
        lines.append(f"  {entry.symbol} = {target} ({adapter.describe(seed, target)})")
        for mode in modes[entry.entity_type]:
            lines.append(f'      mode {mode.id}: reads as "{mode.phrase}" — {mode.predicate}')
    references_user = "\n\n".join([
        context, "WORKSPACE\n" + summarise(seed),
        "ENTITIES TO DESCRIBE, AND THE MODES AVAILABLE FOR EACH\n" + "\n".join(lines),
    ])
    write(step("04_references.prompt.txt"),
          prompt_file("Stage 4 — choose a reference mode per entity", APPROX,
                      _REFERENCES_SYSTEM, references_user,
                      json.dumps({"references": [{"symbol": s, "mode": r.get("proposed")}
                                                 for s, r in references.items()]}, indent=2)))
    write(step("04_references.result.txt"),
          render_references(sequence, adapter, seed, binding, references))

    # -- stage 5
    conditions = "\n".join(
        f"  {r['predicate']}  -> must keep matching exactly one "
        f"{sequence.entry(s).entity_type}" for s, r in references.items()
    )
    populate_user = "\n\n".join([
        context, "WORKSPACE SO FAR\n" + summarise_draft(draft_from_state(seed)),
        "CONDITIONS\n" + conditions,
    ])
    write(step("05_populate.prompt.txt"),
          prompt_file("Stage 5 — pad the world with filler", APPROX
                      + "\nStage 5 is also the one call shown the world in the DRAFT's vocabulary "
                        "(`u1`, `c2`, `m3`)\nrather than in real ids — that is what lets it add a "
                        "message to a conversation that\nalready exists. That view is rebuilt here "
                        "from the shipped state.",
                      _POPULATE_SYSTEM, populate_user, None))
    rejections = [w for w in row["warnings"] if w.startswith("stage 5 dropped")]
    write(
        step("05_populate.result.txt"),
        "Stage 5 result. Filler is folded in ONE ENTITY AT A TIME and each addition kept only if\n"
        "every reference condition still resolves to exactly its own entity. Rejections are\n"
        "recorded, never silently dropped, and Stage 5 cannot fail the task.\n\n"
        f"{len(rejections)} addition(s) rejected:\n"
        + ("\n".join(f"  {r}" for r in rejections) or "  (none)")
        + "\n\nCONDITIONS EVERY ADDITION HAD TO PRESERVE\n" + conditions,
    )

    # -- stage 6
    # `binding` in the record is the POST-replay one, covering rollout symbols too. Replay binds
    # those itself as the steps that create them run, and refuses a symbol that is already bound,
    # so it has to be given the seed half only.
    seed_binding = {s: i for s, i in binding.items() if sequence.entry(s).origin == "seed"}
    replayed = replay(spec, sequence, adapter, seed, seed_binding)
    write(step("06_replay.txt"), render_replay(sequence, adapter, seed, replayed))
    dump_json(step("06_expected_state.json"), row["expected"])

    # -- stage 7
    plan_before = concrete_steps(
        spec, sequence, describe_symbols(sequence, adapter, seed, replayed.binding), {}, observed
    )
    by_key = {s.key: s for s in sequence.steps}
    slot_lines = [
        f"  {by_key[s.key].content[s.param]} — step {sequence.number(s.key)} "
        f"({by_key[s.key].action}.{s.param}): {s.description}"
        for s in sequence.slots if s.kind == "content"
    ]
    if slot_lines:
        content_user = "\n\n".join([
            context, "WORKSPACE\n" + summarise(seed), "PLAN\n" + plan_before,
            "PLACEHOLDERS TO FILL\n" + "\n".join(slot_lines),
        ])
        write(step("07_content.prompt.txt"),
              prompt_file("Stage 7 — write the free text", EXACT, _CONTENT_SYSTEM, content_user,
                          json.dumps({"content": content}, indent=2, ensure_ascii=False)))
    else:
        write(step("07_content.prompt.txt"),
              "# Stage 7 — write the free text\n\n"
              "NO PROMPT EXISTS FOR THIS TASK, and no model call was made.\n\n"
              "`author_content` returns `{}` immediately when a sequence has no `content` slots.\n"
              "Every text param in this sequence is a CARRY — its value is whatever an earlier\n"
              "step returned, supplied by the agent at rollout time — so there was nothing for an\n"
              "author to invent. Six of this pipeline's ten stages call a model; for this task it\n"
              "is five.\n")
    write(
        step("07_content.result.txt"),
        "Stage 7 runs LAST because it is the only stage whose output cannot invalidate anything:\n"
        "`signature` excludes text, emoji and chat names, so the expected state is already fixed\n"
        "by the time a single word is written.\n\n"
        + ("\n".join(f"  {k}\n      {v}" for k, v in content.items()) or "  (no content slots)"),
    )

    # -- stage 8
    plan = concrete_steps(
        spec, sequence, describe_symbols(sequence, adapter, seed, binding), content, observed
    )
    write(step("08_concrete_plan.txt"),
          "The plan once the world exists: real entities described, authored content inlined.\n"
          "Stages 8, 9 and 10 are all held to this.\n\n" + plan)
    items = judge_items(spec, sequence, observed)
    v1_user = "\n\n".join([
        context, "WORKSPACE\n" + summarise(seed), "PLAN (perform in this order)\n" + plan,
        "ITEMS THAT NEED CHECKING\n" + _render_items(items),
    ])
    write(step("08_prompt_v1.prompt.txt"),
          prompt_file("Stage 8 — v1 prompt and the judge specification", EXACT, _V1_SYSTEM, v1_user,
                      json.dumps({"prompt": row["prompts"]["1"],
                                  "judge": [{"id": j["id"], "expected": j["expected"],
                                             "hint": j["hint"]} for j in _judge_at(row, "1")]},
                                 indent=2, ensure_ascii=False)))

    # -- the rewrite rungs
    forbidden = _forbidden(spec, adapter, seed, binding, references)
    stale = stale_references(
        adapter, ChatState.model_validate(row["expected"]), binding, references
    )
    headings = {
        "2": "Stage 9 — rewrite as prose, ids replaced by descriptions",
        "3": "Stage 10 — rewrite as a goal",
        "4": "Stage 11 — fold it into the message a colleague would have typed",
    }
    for level, setting in _REWRITE.items():
        previous = row["prompts"].get(str(int(level) - 1))
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
        user = "\n\n".join([
            context, "WORKSPACE\n" + summarise(seed), f"{setting['plan_label']}\n" + plan,
            f"{setting['reference_label']}\n" + "\n".join(lines),
            "THESE STRINGS MUST NOT APPEAR IN YOUR TEXT\n  " + ", ".join(sorted(forbidden)),
            "JUDGE ITEMS — REWRITE EACH ONE'S expected AND hint FOR YOUR TEXT\n"
            + _render_for_rewrite(_judge_at(row, str(int(level) - 1))),
            "CURRENT TASK TEXT (rewrite this)\n"
            + (previous or "(no rung below exists in this task file)"),
        ])
        shipped = row["prompts"].get(level)
        write(step(f"{7 + int(level):02d}_prompt_v{level}.prompt.txt"),
              prompt_file(headings[level], DRIFTED if shipped else UNBUILT,
                          setting["system"], user,
                          json.dumps({"prompt": shipped}, indent=2, ensure_ascii=False)
                          if shipped else None))

    # -- the ladder, and the eval-time judge call
    write(step("12_ladder.md"),
          render_ladder(sequence, references, binding, row["prompts"], row["judge"],
                        row["warnings"], adapter, seed, stale))
    write(step("13_judge_prompt.txt"), render_judge_prompt(row["judge"]))

    return {
        "idx": idx, "task_id": task_id, "topic": row["topic"], "shape": row["shape"],
        "judge": len(_judge_at(row, "1")), "references": len(references),
        "warnings": len(row["warnings"]),
        "lengths": {k: len(v) for k, v in row["prompts"].items()},
        "modes": sorted({r["mode"] for r in references.values()}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="rebuild_from_samples")
    parser.add_argument("--dataset", default=str(HERE.parent / "samples" / "tasks.jsonl"))
    parser.add_argument("--out", default=str(HERE / "02_authored"))
    args = parser.parse_args()

    spec = json.loads(SPEC_PATH.read_text())
    adapter = ChatAdapter()
    out = Path(args.out)
    rows = [json.loads(line) for line in Path(args.dataset).read_text(encoding="utf-8").splitlines() if line.strip()]

    summaries, failed = [], []
    for row in rows:
        try:
            summaries.append(rebuild(spec, row, adapter, out))
        except Exception as error:  # noqa: BLE001
            failed.append((row.get("task_id"), f"{type(error).__name__}: {error}"))
            print(f"{row.get('task_id')}: FAILED — {type(error).__name__}: {error}", flush=True)
            continue
        print(f"{row['task_id']}: rebuilt", flush=True)

    write(
        out / "LADDER_INDEX.md",
        "# The ladder, across every authored task\n\n"
        "Each row is one task written three ways over one `(seed, expected)` pair and one set of\n"
        "judge items. Open a task's `12_ladder.md` to read the three prompts side by side, or its\n"
        "`08`/`09`/`10_prompt_*.txt` to see the instruction that produced each rewrite.\n\n"
        "`v1 → v2 → v3 chars` is a crude proxy for how much scaffolding each rewrite removed.\n\n"
        "| task | topic | steps | judge items | refs | v1 → v2 → v3 chars | reference modes used |\n"
        "| --- | --- | ---: | ---: | ---: | --- | --- |\n"
        + "\n".join(
            f"| [{s['task_id']}]({s['task_id']}/12_ladder.md) | {s['topic'][:46]} | "
            f"{s['shape']['steps']} | {s['judge']} | {s['references']} | "
            f"{s['lengths']['1']} → {s['lengths']['2']} → {s['lengths']['3']} | "
            f"{', '.join(m.split('_', 1)[1] for m in s['modes'])} |"
            for s in summaries
        )
        + "\n",
    )
    dump_json(out / "rebuild.json", {"rebuilt": summaries, "failed": failed})
    print(f"{len(summaries)} rebuilt, {len(failed)} failed -> {out}")


if __name__ == "__main__":
    main()
