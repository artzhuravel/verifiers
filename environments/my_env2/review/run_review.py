"""Run the pipeline one stage at a time and write every artifact out for a human to read.

`pipeline.build_task` runs the same ten stages and keeps only the finished `TaskRecord`. This
mirrors it and dumps what happens in between: the prompt each authoring call actually received,
the reply it gave, and the derived artifact each stage produced. Nothing here is used by the
pipeline itself — it is a review harness, and it exists so the stages can be inspected without
re-reading the code that produced them.

    uv run --with-editable environments/my_env2 \
        python environments/my_env2/review/run_review.py --tasks 1,3,9,12

Needs OPENROUTER_BASE_URL and OPENROUTER_API_KEY. Seven model calls per task plus any
correction rounds; the cache under `--cache` makes a re-run free for the stages that already
succeeded.
"""

import argparse
import json
import random
import re
import sys
from dataclasses import asdict
from pathlib import Path

from my_env2.adapter import ChatAdapter
from my_env2.authoring import assign_references, author_content, author_world, populate
from my_env2.llm import Author, AuthoringError
from my_env2.pipeline import DEFAULT_CONFIGS, SPEC_PATH, TaskRecord
from my_env2.prompts import (
    LEVELS,
    author_v1,
    describe_symbols,
    judge_items,
    rewrite_prompt,
    stale_references,
)
from my_env2.render import concrete_steps, manifest_brief, shared_context, symbolic_steps
from my_env2.replay import expected_facts, replay
from my_env2.seed import DraftError, build, summarise
from my_env2.symbolic import Sequence, generate_sequence

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))  # so `tests.stub` is importable without installing tests

from tests.stub import stub_world  # noqa: E402


class _Logging:
    """Shared by both authors below: a round-trip log, and a place for the driver to leave
    whatever a canned reply needs to be shaped correctly."""

    def _init_log(self) -> None:
        self.log: list[dict] = []

    def stash(self, **values) -> None:
        self.__dict__.update(values)

    def rounds(self, task_id: str, stage: str) -> list[dict]:
        return [e for e in self.log if e["task_id"] == task_id and e["stage"] == stage]


class RecordingAuthor(_Logging, Author):
    """An `Author` that keeps every round-trip, in order, including correction rounds."""

    def __post_init__(self) -> None:
        super().__post_init__()
        self._init_log()

    def _call(self, task_id: str, stage: str, system: str, user: str) -> dict:
        reply = super()._call(task_id, stage, system, user)
        self.log.append(
            {"task_id": task_id, "stage": stage, "system": system, "user": user, "reply": reply}
        )
        return reply


class OfflineAuthor(_Logging, Author):
    """No model behind it, so every PROMPT it records is real and every reply is canned.

    This exists for one reason: stages 4 and 5 run against the *core* world, which no shipped
    task record preserves, so their prompts cannot be reconstructed after the fact. Driving the
    pipeline with a mechanical world makes those two prompts exact — dull world, real prompt.

    Each canned reply is still put through the stage's own `validate`, so a reply that would not
    have satisfied the real contract fails here too rather than producing a misleading artifact.
    """

    def __post_init__(self) -> None:
        super().__post_init__()
        self._init_log()

    def ask(self, task_id, stage, system, user, validate=None):  # noqa: ANN001, ANN201
        reply = self._canned(stage, user)
        self.log.append(
            {"task_id": task_id, "stage": stage, "system": system, "user": user, "reply": reply}
        )
        if validate is not None:
            validate(reply)  # the real contract check, on a canned answer
        return reply

    def _canned(self, stage: str, user: str) -> dict:
        if stage == "world":
            return stub_world(self.sequence).model_dump(mode="json")
        if stage == "references":
            # Empty on purpose: `assign_references` then takes its deterministic path and tries
            # every declared mode in order, which is the fallback worth exercising.
            return {"references": []}
        if stage == "populate":
            people = [u.ref for u in self.core_draft.users]
            return {
                "new_users": [{"ref": "n1", "name": "Filler One", "handle": "filler1"}],
                "new_chats": [{"ref": "n2", "name": "watercooler", "members": [people[0], "n1"]}],
                "new_messages": [
                    {"ref": "n3", "chat": "n2", "sender": "n1", "order": 99,
                     "text": "unrelated chatter about the coffee machine", "read_by_actor": True},
                ],
            }
        if stage == "content":
            wanted = re.findall(r"^\s+(\$\S+) —", user, re.MULTILINE)
            return {"content": {name: f"canned text for {name}" for name in wanted}}
        if stage == "prompt_v1":
            items = judge_items(self.spec, self.sequence, self.observed)
            return {
                "prompt": "CANNED v1 text — this run exists for the prompts, not the prose.",
                "judge": [
                    {"id": item["id"], "expected": "canned expected answer",
                     "hint": item["delivered_in"]}
                    for item in items
                ],
            }
        if stage.startswith("prompt_v"):
            # Item ids derive from step keys and so are identical at every rung, which is what
            # lets one derivation satisfy `_rewrite_judge` at all three rewrite stages.
            items = judge_items(self.spec, self.sequence, self.observed)
            return {
                "prompt": f"CANNED {stage} text — this run exists for the prompts.",
                "judge": [
                    {"id": item["id"], "expected": f"canned expected, restated at {stage}",
                     "hint": item["delivered_in"]}
                    for item in items
                ],
            }
        raise AuthoringError(f"no canned reply for stage {stage!r}")


# --- writing ---------------------------------------------------------------------------


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def dump_json(path: Path, value) -> Path:
    return write(path, json.dumps(value, indent=2, ensure_ascii=False))


def call_log(title: str, rounds: list[dict]) -> str:
    """One stage's model calls, prompts and replies, as one readable file."""
    if not rounds:
        return f"# {title}\n\n(no model call was made — the stage fell back or failed early)"
    blocks = [f"# {title}", "", f"{len(rounds)} model call(s)."]
    for number, entry in enumerate(rounds, 1):
        label = f"call {number} of {len(rounds)}"
        if number > 1:
            label += "  (correction round: the previous reply was rejected, see the tail of USER)"
        blocks += [
            "",
            "=" * 96,
            f"== {label}",
            "=" * 96,
            "",
            "-" * 96,
            "-- SYSTEM PROMPT",
            "-" * 96,
            entry["system"],
            "",
            "-" * 96,
            "-- USER PROMPT",
            "-" * 96,
            entry["user"],
            "",
            "-" * 96,
            "-- REPLY",
            "-" * 96,
            json.dumps(entry["reply"], indent=2, ensure_ascii=False),
        ]
    return "\n".join(blocks)


# --- stage 1 rendering -----------------------------------------------------------------


def render_timeline(sequence: Sequence) -> str:
    """The threads over their shared clock — what makes this a walk and not a sample."""
    threads = len(sequence.timelines)
    turns = len(sequence.timelines[0]) if threads else 0
    last = [
        max((t for t in range(turns) if sequence.timelines[c][t]), default=-1)
        for c in range(threads)
    ]
    width = 34
    lines = ["turn  " + "".join(f"thread {c}".ljust(width) for c in range(threads))]
    for turn in range(turns):
        cells = []
        for chain in range(threads):
            emitted = sequence.timelines[chain][turn]
            if emitted:
                cell = "; ".join(
                    f"{sequence.number(s.key)}. {s.action}" + (" (aside)" if s.unrelated else "")
                    for s in emitted
                )
            else:
                cell = "·  (skipped)" if turn < last[chain] else "—"
            cells.append(cell.ljust(width))
        lines.append(f"{turn:>4}  " + "".join(cells).rstrip())
    return "\n".join(lines)


def render_edges(sequence: Sequence) -> str:
    rows = []
    for step in sequence.steps:
        number = sequence.number(step.key)
        for edge in step.depends_on:
            source = sequence.step(edge["source"])
            kind = "OBJECT (an entity id — the state diff can see it)" if edge["via"] == "object" \
                else "VALUE  (what a read returned — only the judge can see it)"
            cross = " [cross-thread]" if source.chain != step.chain else ""
            rows.append(
                f"  step {sequence.number(edge['source'])} ({source.action})"
                f"  ->  step {number} ({step.action}).{edge['param']}{cross}\n"
                f"        {kind}"
            )
    return "\n".join(rows) or "  (none — every step is a root)"


_SENT = "[SENT — this block appears VERBATIM in the Stage 3 prompt, under the header named below]"
_REVIEW = "[REVIEW ONLY — this block is written for a human and is never sent to any model]"


def render_sequence(spec: dict, sequence: Sequence, idx: int) -> str:
    return "\n\n".join(
        [
            f"SEQUENCE idx {idx}  (task id {sequence.task_id})",
            "Stage 1 output. No world exists yet: every entity is a typed placeholder, and the\n"
            "world is authored afterwards to satisfy what is written here.\n"
            "\n"
            "WHAT OF THIS THE AUTHORING MODEL ACTUALLY SEES\n"
            "Only two of the blocks below are prompt content; each is tagged. The rest is written\n"
            "for you. The full Stage 3 user message is, in order:\n"
            "\n"
            "    ENVIRONMENT / ENTITY TYPES IN THIS TASK / ACTIONS THIS TASK USES   <- 02_shared_context.txt\n"
            "    PLAN THE AGENT WILL BE ASKED TO CARRY OUT                          <- the tagged block below\n"
            "    PLACEHOLDERS THAT MUST ALREADY EXIST                               <- the tagged block below\n"
            "    BIND EXACTLY THESE, ONE EACH, AND NOTHING ELSE                     <- one line, not shown here\n"
            "\n"
            "plus a system prompt. For the real thing, byte for byte, read 03_world.prompt.txt.",
            f"SHAPE (measured off the emitted steps, not read back from the config)\n{_REVIEW}\n"
            + "\n".join(f"  {k:26} {json.dumps(v)}" for k, v in sequence.shape.items()),
            "THE CLOCK — three threads advancing in parallel; a thread may skip a turn to wait\n"
            f"for another thread to produce something it can consume\n{_REVIEW}\n"
            + render_timeline(sequence),
            "THE PLAN, AS THE AUTHORING MODEL SEES IT\n"
            f'{_SENT}\nheader in the prompt: "PLAN THE AGENT WILL BE ASKED TO CARRY OUT"\n'
            + symbolic_steps(spec, sequence),
            "DEPENDENCY EDGES — the reason this is a chain and not a list\n"
            f"{_REVIEW}\n"
            "The model is never handed this table. It learns the edges only from lines inside the\n"
            "plan block above — `text <- must carry what step N returned` for a value edge, and\n"
            "`= $new_x_0 (the x step N creates)` for an object edge.\n"
            + render_edges(sequence),
            "PLACEHOLDERS THAT MUST ALREADY EXIST\n"
            f'{_SENT}\nheader in the prompt: "PLACEHOLDERS THAT MUST ALREADY EXIST" (Stage 3 only)\n'
            "A REQUIRED line is what stops a step being a no-op.\n" + manifest_brief(sequence),
            "SLOTS THE AUTHORING PASSES MUST FILL\n"
            f"{_REVIEW}\n"
            "Not sent as a block. `sequence.slots` is what Stage 7 turns into its own\n"
            "PLACEHOLDERS TO FILL list, and what Stage 8 derives the judge items from.\n"
            + (
                "\n".join(
                    f"  step {sequence.number(s.key):>2} {s.param:12} [{s.kind}]"
                    + (f" <- from step(s) {', '.join(str(sequence.number(k)) for k in s.sources)}"
                       if s.sources else "")
                    + f"\n        {s.description}"
                    for s in sequence.slots
                )
                or "  (none)"
            ),
        ]
    )


# --- stage 4/5/6 rendering -------------------------------------------------------------


def render_references(sequence, adapter, state, binding, references) -> str:
    lines = [
        "Stage 4. Each seed entity gets ONE way of being described instead of named.",
        "The model picks only WHICH mode; the adapter derives the params from the world and",
        "proves resolve(state, mode, params) == [that entity]. A mode that cannot be made to fit",
        "is skipped and the next tried, so the stage is total — an entity with no working",
        "reference raises, because v2 strips ids out and the task would be unanswerable.",
        "",
    ]
    for symbol, reference in references.items():
        target = binding[symbol]
        resolved = adapter.resolve(state, reference["mode"], reference["params"])
        proposed = reference.get("proposed")
        lines += [
            f"  {symbol}  ->  {target}",
            f"      the entity      {adapter.describe(state, target)}",
            f"      mode chosen     {reference['mode']}"
            + (
                "  (the model's pick)"
                if proposed == reference["mode"]
                else f"  (model proposed {proposed!r}; it did not fit, this is the fallback)"
            ),
            f"      params derived  {json.dumps(reference['params'], ensure_ascii=False)}",
            f"      reads as        \"{reference['phrase']}\"",
            f"      predicate       {reference['predicate']}",
            f"      PROOF           resolve() -> {resolved}"
            f"   {'unique, and it is the target' if resolved == [target] else 'MISMATCH'}",
            "",
        ]
    return "\n".join(lines)


def render_replay(sequence, adapter, seed, replayed) -> str:
    lines = [
        "Stage 6. Bind every placeholder, execute the sequence once against the seed.",
        "This produces `expected` — the deterministic reward's comparison target — and it is the",
        "pipeline's validity gate: a step that errors, a write that changed nothing, or a read",
        "that came back empty drops the task rather than shipping a hole in its own scoring.",
        "",
        "Free text is NOT resolved here. Replay writes the placeholder itself into message",
        "bodies, because `signature` excludes text — which is what lets Stage 7 decide what the",
        "messages say afterwards without moving a single fact in `expected`.",
        "",
        "BINDING (symbol -> real id)",
    ]
    for symbol, entity_id in replayed.binding.items():
        origin = sequence.entry(symbol).origin
        lines.append(f"  {symbol:20} {entity_id:12} ({origin})")

    lines += ["", "STEP BY STEP"]
    for step in sequence.steps:
        number = sequence.number(step.key)
        if step.key not in replayed.args:
            lines.append(f"  step {number:>2} {step.action:20} EXTERNAL — skipped by replay")
            continue
        lines.append(f"  step {number:>2} {step.action:20} [{step.kind}]")
        lines.append(f"        args      {json.dumps(replayed.args[step.key], ensure_ascii=False)}")
        delta = replayed.step_deltas.get(step.key) or []
        if delta:
            lines.append(f"        adds      {delta}")
        elif step.kind == "read":
            lines.append("        adds      nothing — a read has no state effect, which is why it "
                         "needs a judge item to be scorable at all")
        else:
            lines.append("        adds      NOTHING — a write with no state footprint. This is a "
                         "no-op and drops the task.")
        if step.key in replayed.observed:
            text = replayed.observed[step.key]
            lines.append(f"        returned  {text[:600]}{' …' if len(text) > 600 else ''}")

    lines += [
        "",
        "PER-TURN DIFFS (recorded, deliberately not scored — they say which turn a failed "
        "rollout stopped matching at)",
    ]
    for entry in replayed.turn_diffs:
        lines.append(f"  turn {entry['turn']}: {entry['added'] or '(nothing)'}")

    lines += [
        "",
        f"no-op writes : {replayed.no_ops or 'none'}",
        f"empty reads  : {replayed.barren or 'none'}",
        "",
        "WHAT THE DETERMINISTIC REWARD WILL LOOK FOR (expected minus seed, over `signature`)",
    ]
    lines += [f"  {fact}" for fact in expected_facts(adapter, seed, replayed.expected)]
    return "\n".join(lines)


def render_judge_prompt(judges) -> str:
    """The eval-time judge prompt, once per rung — the items are restated at each one."""
    if isinstance(judges, list):  # a task file from before the items were restated per level
        judges = {"1": judges}
    blocks = [
        "# The delivery judge (eval time — after a rollout)",
        "",
        "Not part of authoring. This is the one model call made while *scoring*, and it is the",
        "whole of the `delivery` component (0.4 of the reward). One call per task, however many",
        "items. The judge grades over the WHOLE rollout — every tool call and every result — so",
        "that a retrieved answer can be told from an invented one, and so that information landing",
        "in a message partway through counts. It is not graded off the final reply alone.",
        "",
        "The items differ per level: each rung restates them for its own text, since the higher",
        "rungs remove the step numbers and ids the lower ones lean on. One section per level below.",
    ]
    for level, items in judges.items():
        blocks += ["", "=" * 96, f"== LEVEL {level}", "=" * 96, "", _one_judge_prompt(items)]
    return "\n".join(blocks)


def _one_judge_prompt(judge: list[dict]) -> str:
    """The eval-time delivery judge's prompt — the eighth LLM call in a task's life.

    Everything but the transcript is knowable now: the items come from the record, and the
    template is `verify._JUDGE_PROMPT`. The transcript is produced by `verify.transcript` from a
    rollout, so its content cannot exist before an agent has run — its two sections are shown in
    place instead.
    """
    from my_env2.verify import _JUDGE_PROMPT

    if not judge:
        return ("This task has NO judge items, so `judge_score` returns 1.0 without calling a "
                "model at all. The `delivery` component — 0.4 of the reward — is free here.")
    items = "\n".join(
        f"{number}. {item['requirement']}\n"
        f"   A correct answer says: {item['expected']}\n"
        f"   Where to look: {item['hint']}"
        for number, item in enumerate(judge, 1)
    )
    placeholder = (
        "=== FULL ROLLOUT — every tool call the agent made and every result that came back ===\n"
        "    <<< the agent's transcript — only exists once a rollout has run >>>\n\n"
        "=== WHAT THE AGENT DELIVERED — the same messages, collected for convenience ===\n"
        "Messages the agent sent during this rollout:\n"
        "    <<< every message the acting user sent during the rollout, seeded history excluded >>>\n\n"
        "Agent's final reply:\n"
        "    <<< the agent's last reply >>>"
    )
    return "\n".join([
        "-" * 96,
        "-- PROMPT (verify._JUDGE_PROMPT, filled in)",
        "-" * 96,
        _JUDGE_PROMPT.format(items=items, transcript=placeholder),
    ])


_LADDER_TITLES = {
    "1": "L1 — explicit, numbered, ids named. The floor.",
    "2": "L2 — prose. Every id replaced by the description proved to single it out, so the agent "
         "must inspect the workspace before it can act at all.",
    "3": "L3 — the goal. No step individually identifiable.",
    "4": "L4 — folded. Actions that existed only to feed each other become one request, no content "
         "is dictated word for word, and no clause narrates a hand-off.",
}


def render_ladder(sequence, references, binding, prompts, judges, warnings, adapter, seed,
                  stale=frozenset()) -> str:
    if isinstance(judges, list):  # a task file from before the items were restated per level
        judges = {"1": judges}
    lines = [
        f"# The ladder — {sequence.task_id}",
        "",
        "The same work asked for four ways, over one `(seed, expected)` pair. Nothing but the",
        "specification's explicitness differs, so a score gap between two levels measures the gap",
        "and not authoring noise.",
        "",
        "The judge items say the same thing at every rung but are **restated** for each, because a",
        "rung that removes step numbers and ids leaves an item written against the rung below",
        "describing a task the agent was never given.",
        "",
        "## How each thing is referred to",
        "",
        "A description is meant to be used **once**, to introduce a thing; later mentions refer",
        "back. `uses` counts how many times each rung pasted the description verbatim — anything",
        "above 1 is the defect.",
        "",
        "| symbol | entity | v1 says | the description | uses in v2/v3/v4 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for symbol, reference in references.items():
        target = binding[symbol]
        described = adapter.describe(seed, target).replace("|", "\\|")
        counts = "/".join(
            str(prompts[level].count(reference["phrase"])) for level in ("2", "3", "4")
            if level in prompts
        )
        note = "  **[the work makes this false]**" if symbol in stale else ""
        lines.append(
            f"| `{symbol}` | {described[:64]} | `{target}` | \"{reference['phrase']}\"{note} "
            f"| {counts} |"
        )

    for level in [lvl for lvl in ("1", "2", "3", "4") if lvl in prompts]:
        lines += ["", f"## {_LADDER_TITLES[level]}", "", "```text", prompts[level], "```"]
        items = judges.get(level)
        if items is None:
            continue
        lines += ["", f"### What the judge checks at L{level}", ""]
        if not items:
            lines.append(
                "**(none)** — this sequence has no value edge and no uncarried read, so nothing "
                "needed judging. The `delivery` component scores 1.0 for free here, and 0.4 of "
                "this task's reward is vacuous."
            )
        for item in items:
            lines += [
                f"- **{item['id']}**",
                f"    - a correct answer says: {item['expected']}",
                f"    - where to look: {item['hint']}",
            ]

    lines += ["", "## Warnings recorded for this task", ""]
    lines += [f"- {w}" for w in warnings] or ["(none)"]
    return "\n".join(lines)


# --- the driver ------------------------------------------------------------------------


def review_task(spec, idx, author, adapter: ChatAdapter, out: Path, subdir: str):
    """`build_task`, stage by stage, writing everything out. Returns the record, or raises."""
    task_id = f"t{idx}"
    directory = out / subdir / task_id
    step = lambda name: directory / name  # noqa: E731

    # -- stage 1
    sequence = generate_sequence(spec, random.Random(idx), DEFAULT_CONFIGS, task_id=task_id)
    author.stash(spec=spec, sequence=sequence, observed={})
    write(step("01_sequence.txt"), render_sequence(spec, sequence, idx))
    dump_json(
        step("01_sequence.json"),
        {
            "task_id": task_id,
            "shape": sequence.shape,
            "steps": [asdict(s) for s in sequence.steps],
            "manifest": [asdict(m) for m in sequence.manifest],
            "slots": [asdict(s) for s in sequence.slots],
        },
    )

    # -- stage 2
    write(
        step("02_shared_context.txt"),
        "Stage 2. Built once and prepended to EVERY authoring call below, so that all seven\n"
        "decide against the same account of what the environment means. Every word of it comes\n"
        "from the spec — an action's description, a param's description, an entity type's\n"
        "description, an action's `returns`.\n\n" + shared_context(spec, sequence),
    )

    # -- stage 3
    draft, context = author_world(author, spec, sequence)
    core_state, core_binding = build(draft, sequence.seed_entities())
    write(step("03_world.prompt.txt"), call_log("Stage 3 — invent the core world", author.rounds(task_id, "world")))
    write(
        step("03_world.result.txt"),
        "Stage 3 result: the authored draft, built into a state.\n"
        "`seed.build` validates and never repairs — an undeclared sender, a reply across chats\n"
        "or an unbound placeholder rejects the whole draft and costs a correction round.\n\n"
        f"topic: {draft.topic}\n\n"
        + summarise(core_state)
        + "\n\nPLACEHOLDERS BOUND\n"
        + "\n".join(f"  {s:20} -> {i}" for s, i in core_binding.items()),
    )

    # -- stage 4
    references = assign_references(author, spec, sequence, adapter, core_state, core_binding, context)
    write(step("04_references.prompt.txt"), call_log("Stage 4 — choose a reference mode per entity", author.rounds(task_id, "references")))
    write(step("04_references.result.txt"), render_references(sequence, adapter, core_state, core_binding, references))

    # -- stage 5
    author.stash(core_draft=draft)
    populated, rejected = populate(author, spec, sequence, adapter, draft, references, context)
    seed, binding = build(populated, sequence.seed_entities())
    for symbol, reference in references.items():
        resolved = adapter.resolve(seed, reference["mode"], reference["params"])
        if resolved != [binding[symbol]]:
            raise DraftError(f"{reference['predicate']!r} resolves to {resolved}, not {binding[symbol]}")
    write(step("05_populate.prompt.txt"), call_log("Stage 5 — pad the world with filler", author.rounds(task_id, "populate")))
    write(
        step("05_populate.result.txt"),
        "Stage 5 result. Filler is folded in ONE ENTITY AT A TIME and each addition kept only if\n"
        "every reference condition still resolves to exactly its own entity. Rejections are\n"
        "recorded, never silently dropped, and Stage 5 cannot fail the task — a world without\n"
        "padding is weaker, not broken.\n\n"
        f"core     : {len(draft.users)} people, {len(draft.chats)} chats, {len(draft.messages)} messages\n"
        f"populated: {len(populated.users)} people, {len(populated.chats)} chats, "
        f"{len(populated.messages)} messages\n\n"
        "REJECTED ADDITIONS\n"
        + ("\n".join(f"  {reason}" for reason in rejected) or "  (none)")
        + "\n\nTHE SEED THAT SHIPS\n"
        + summarise(seed),
    )

    # -- stage 6
    replayed = replay(spec, sequence, adapter, seed, binding)
    if wasted := replayed.no_ops + replayed.barren:
        raise RuntimeError(
            "nothing observable came of "
            + ", ".join(f"step {sequence.number(k)} ({sequence.step(k).action})" for k in wasted)
        )
    write(step("06_replay.txt"), render_replay(sequence, adapter, seed, replayed))
    dump_json(step("06_expected_state.json"), replayed.expected.model_dump())

    # -- stage 7
    author.stash(observed=replayed.observed)
    plan_before_content = concrete_steps(
        spec, sequence, describe_symbols(sequence, adapter, seed, replayed.binding), {}, replayed.observed
    )
    content = author_content(author, sequence, seed, plan_before_content, context)
    write(step("07_content.prompt.txt"), call_log("Stage 7 — write the free text", author.rounds(task_id, "content")))
    write(
        step("07_content.result.txt"),
        "Stage 7 result. This runs LAST because it is the only stage whose output cannot\n"
        "invalidate anything: `signature` excludes text, so the expected state is already fixed.\n\n"
        + ("\n".join(f"  {k}\n      {v}" for k, v in content.items()) or "  (no content slots)"),
    )

    # -- stages 8, 9, 10
    v1, judge, plan = author_v1(author, spec, sequence, adapter, seed, binding, content, replayed.observed, context)
    write(step("08_prompt_v1.prompt.txt"), call_log("Stage 8 — v1 prompt and the judge specification", author.rounds(task_id, "prompt_v1")))
    write(step("08_concrete_plan.txt"),
          "The plan once the world exists: real entities described, authored content inlined.\n"
          "This is what every rung is held to.\n\n" + plan)

    stale = stale_references(adapter, replayed.expected, binding, references)
    warnings = [f"stage 5 dropped: {reason}" for reason in rejected]
    if stale:
        warnings.append(
            "the task's own work invalidates: "
            + ", ".join(f"{s} ({references[s]['phrase']!r})" for s in sorted(stale))
        )

    titles = {"2": "Stage 9 — rewrite as prose, ids replaced by descriptions",
              "3": "Stage 10 — rewrite as a goal",
              "4": "Stage 11 — fold it into the message a colleague would have typed"}
    prompts, judges = {"1": v1}, {"1": judge}
    for level in LEVELS[1:]:
        previous = LEVELS[LEVELS.index(level) - 1]
        text, restated, complaints = rewrite_prompt(
            author, level, spec, sequence, adapter, seed, binding, references, plan,
            prompts[previous], judges[previous], stale, context,
        )
        prompts[level], judges[level] = text, restated
        warnings += [f"v{level}: {c}" for c in complaints]
        write(step(f"{7 + int(level):02d}_prompt_v{level}.prompt.txt"),
              call_log(titles[level], author.rounds(task_id, f"prompt_v{level}")))

    for symbol, reference in references.items():
        phrase = str(reference["params"].get("text", "")).casefold()
        if phrase and any(phrase in text.casefold() for text in content.values()):
            warnings.append(f"authored content repeats the phrase {reference['phrase']!r}")

    write(step("12_ladder.md"), render_ladder(sequence, references, binding, prompts, judges, warnings, adapter, seed, stale))
    write(step("13_judge_prompt.txt"), render_judge_prompt(judges))

    record = TaskRecord(
        task_id=task_id, idx=idx, topic=populated.topic,
        seed=seed.model_dump(), expected=replayed.expected.model_dump(),
        prompts=prompts, judge=judges,
        steps=[asdict(s) for s in sequence.steps],
        manifest=[asdict(m) for m in sequence.manifest],
        slots=[asdict(s) for s in sequence.slots],
        binding=replayed.binding, references=references, content=content,
        observed=replayed.observed, args=replayed.args,
        step_deltas=replayed.step_deltas, turn_diffs=replayed.turn_diffs,
        expected_facts=expected_facts(adapter, seed, replayed.expected),
        shape=sequence.shape, warnings=warnings,
    )
    dump_json(step("12_record.json"), asdict(record))
    return record


def main() -> None:
    parser = argparse.ArgumentParser(prog="run_review")
    parser.add_argument("--tasks", default="1,3,9,12", help="indices to author in full")
    parser.add_argument("--sequences", default="0,1,2,3,4,5,6,7,8,9",
                        help="indices to dump Stage 1 for (offline, free)")
    parser.add_argument("--model", default="openai/gpt-5-mini")
    parser.add_argument("--cache", default="tmp/my_env2_review_cache")
    parser.add_argument("--out", default=str(HERE))
    parser.add_argument(
        "--offline", action="store_true",
        help="no API key: drive the pipeline with a mechanical world and canned replies, so every "
             "PROMPT is exact even though no prose is authored",
    )
    args = parser.parse_args()

    spec = json.loads(SPEC_PATH.read_text())
    out = Path(args.out)
    adapter = ChatAdapter()

    # Stage 1 for a spread of indices — no model, no world, no cost.
    rows = []
    for idx in [int(i) for i in args.sequences.split(",") if i.strip()]:
        sequence = generate_sequence(spec, random.Random(idx), DEFAULT_CONFIGS, task_id=f"t{idx}")
        write(out / "01_sequences" / f"seq_{idx:02d}.txt", render_sequence(spec, sequence, idx))
        rows.append((idx, sequence))
    write(
        out / "01_sequences" / "SUMMARY.md",
        "# Stage 1 over a spread of indices\n\n"
        "Generated offline: no world, no model, no cost. `longest chain` is the longest path\n"
        "through the DAG; `links/thread` counts each thread's own emissions, which is a\n"
        "different number whenever a thread's links all hang off one foreign source.\n\n"
        "| idx | steps | longest chain | links/thread | object edges | value edges | "
        "cross-thread | external | asides | seed entities | actions |\n"
        "| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |\n"
        + "\n".join(
            f"| [{i}](seq_{i:02d}.txt) | {s.shape['steps']} | {s.shape['longest_chain']} | "
            f"{s.shape['links_per_thread']} | {s.shape['object_edges']} | {s.shape['value_edges']} | "
            f"{s.shape['cross_thread_edges']} | {s.shape['external_steps']} | "
            f"{s.shape['distractors']} | {len(s.seed_entities())} | "
            + ", ".join(f"{k}×{v}" for k, v in s.shape["actions"].items())
            + " |"
            for i, s in rows
        ),
    )
    print(f"wrote Stage 1 for {len(rows)} sequence(s)")

    subdir = "04_offline_exact_prompts" if args.offline else "03_live"
    author = (
        OfflineAuthor(model="(none — offline)", cache_dir=args.cache)
        if args.offline
        else RecordingAuthor(model=args.model, cache_dir=args.cache)
    )
    records, dropped = [], []
    for idx in [int(i) for i in args.tasks.split(",") if i.strip()]:
        try:
            record = review_task(spec, idx, author, adapter, out, subdir)
        except Exception as error:  # noqa: BLE001 - report and carry on, as the pipeline does
            dropped.append((idx, f"{type(error).__name__}: {error}"))
            print(f"idx {idx}: DROPPED — {type(error).__name__}: {error}", flush=True)
            continue
        records.append(record)
        print(
            f"idx {idx}: {record.shape['steps']} steps, "
            f"{len(record.judge['1'])} judge item(s), "
            f"{len(record.references)} reference(s), {len(record.warnings)} warning(s)",
            flush=True,
        )

    if records:
        write(
            out / subdir / "tasks.jsonl",
            "\n".join(json.dumps(asdict(r), ensure_ascii=False) for r in records),
        )
    dump_json(
        out / subdir / "run.json",
        {
            "model": args.model,
            "authored": [r.idx for r in records],
            "dropped": dropped,
            "model_calls": author.calls,
            "cache_hits": author.cache_hits,
            "calls_by_stage": {
                stage: sum(1 for e in author.log if e["stage"] == stage)
                for stage in dict.fromkeys(e["stage"] for e in author.log)
            },
        },
    )
    print(f"{len(records)} authored, {len(dropped)} dropped — "
          f"{author.calls} model call(s), {author.cache_hits} from cache")


if __name__ == "__main__":
    main()
