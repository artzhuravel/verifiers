"""The pipeline: an index in, one persisted task out.

Each stage is a proposal about a task that does not exist yet, and this is the file that makes
them meet in the right order and refuses the ones that do not fit. Two properties are worth
stating outright, because everything else follows from them:

**Nothing is repaired.** A stage either satisfies its contract or the task is dropped. The
alternative — patching a draft, or a prompt, into something buildable — produces tasks whose
prompt describes a world other than the one shipped, and no amount of scoring catches that.

**The expensive half runs last and cannot invalidate the cheap half.** By the time any prose is
written, `(seed, expected)` is fixed and every reference has been proved to resolve. Free text
is excluded from `signature`, so Stage 7 onwards can decide what the messages say without a
single fact moving.

    python -m my_env2.pipeline --num 5 --model openai/gpt-5-nano --out tmp/tasks_v2.jsonl
"""

import argparse
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from my_env2.adapter import ChatAdapter
from my_env2.authoring import assign_references, author_content, author_world, populate
from my_env2.llm import Author
from my_env2.prompts import (
    LEVELS,
    author_v1,
    describe_symbols,
    rewrite_prompt,
    stale_references,
)
from my_env2.render import concrete_steps
from my_env2.replay import ReplayError, expected_facts, replay
from my_env2.seed import DraftError, build
from my_env2.symbolic import ChainConfig, generate_sequence

SPEC_PATH = Path(__file__).parent / "action_spec.json"

DEFAULT_CONFIGS = [
    ChainConfig(max_depth=3, max_breadth=2, p_cross=0.4),
    ChainConfig(max_depth=2, max_breadth=2, p_skip=0.3, p_cross=0.5, p_unrelated=0.2),
    ChainConfig(max_depth=1, p_cross=0.5),
]
"""Three threads: one that mostly follows its own errand, one that skips turns and picks up the
first thread's work, and a single-link one. The first two are the smallest configuration in which
a prompt has to describe two strands of work that genuinely depend on each other. The third is
there because a one-link thread may open with an action that produces nothing, and that is the
only route by which an action needing pre-existing history — `mark_read` — can reach a task as
real work rather than as a distractor."""


@dataclass
class TaskRecord:
    """Everything about one task, in one row.

    The shape metadata is not only for debugging. Once rollouts exist, observed difficulty can
    be regressed on realized structure — depth, cross-thread edges, fan-in, how many references
    are superlatives — which is what makes it possible to *sample* toward a difficulty mixture
    instead of generating broadly and filtering after.
    """

    task_id: str
    idx: int
    topic: str
    seed: dict
    expected: dict
    prompts: dict[str, str]
    judge: dict[str, list[dict]]
    """Level -> the judge specification restated for that level's prompt. Keyed, not a single
    list, because an item written against v1 names steps and ids the higher rungs remove — a
    grader handed the v1 item while reading a v4 rollout is checking a task nobody was given."""
    steps: list[dict]
    manifest: list[dict]
    slots: list[dict]
    binding: dict[str, str]
    references: dict[str, dict]
    content: dict[str, str]
    observed: dict[str, str]
    args: dict[str, dict]
    step_deltas: dict[str, list[str]]
    turn_diffs: list[dict]
    expected_facts: list[str]
    shape: dict
    warnings: list[str] = field(default_factory=list)


def build_task(
    spec: dict,
    idx: int,
    author: Author,
    configs: list[ChainConfig] | None = None,
    adapter: ChatAdapter | None = None,
) -> TaskRecord:
    """One task, or an exception naming the stage that refused it."""
    adapter = adapter or ChatAdapter()
    sequence = generate_sequence(
        spec, random.Random(idx), configs or DEFAULT_CONFIGS, task_id=f"t{idx}"
    )

    draft, context = author_world(author, spec, sequence)
    # References are chosen against the core world, before padding. Uniqueness only gets harder
    # as entities are added, so Stage 5 is where it is defended; choosing here keeps the
    # descriptions about the entities the task is actually about.
    core_state, core_binding = build(draft, sequence.seed_entities())
    references = assign_references(
        author, spec, sequence, adapter, core_state, core_binding, context
    )

    populated, rejected = populate(
        author, spec, sequence, adapter, draft, references, context
    )
    seed, binding = build(populated, sequence.seed_entities())
    # The incremental check inside `populate` runs against a draft being extended one entity at
    # a time; this one runs against the state that actually ships. They should agree, and a
    # disagreement means the two builds disagree — which would be a bug worth failing on, not a
    # warning worth printing.
    for symbol, reference in references.items():
        resolved = adapter.resolve(seed, reference["mode"], reference["params"])
        if resolved != [binding[symbol]]:
            raise DraftError(
                f"{reference['predicate']!r} resolves to {resolved}, not {binding[symbol]}"
            )

    replayed = replay(spec, sequence, adapter, seed, binding)
    # Every REQUIRED line in the manifest exists to prevent these two. A step whose effect the
    # reward cannot see, or a read with nothing in it to find, is a step the task cannot honestly
    # ask for — so the world was authored wrong and the task goes rather than shipping a hole in
    # its own scoring.
    if wasted := replayed.no_ops + replayed.barren:
        raise ReplayError(
            "nothing observable came of "
            + ", ".join(
                f"step {sequence.number(key)} ({sequence.step(key).action})"
                for key in wasted
            )
        )

    content = author_content(
        author,
        sequence,
        seed,
        concrete_steps(
            spec,
            sequence,
            describe_symbols(sequence, adapter, seed, replayed.binding),
            {},
            replayed.observed,
        ),
        context,
    )

    v1, judge, plan = author_v1(
        author,
        spec,
        sequence,
        adapter,
        seed,
        binding,
        content,
        replayed.observed,
        context,
    )

    # A description proved unique against the seed can still depend on something the task's own
    # steps destroy — the measured case is a chat described as the only one with anything unread,
    # in a task that marks it read. The rewrite stages are told which, so they introduce such a
    # thing before the work that breaks it instead of naming it that way again afterwards.
    stale = stale_references(adapter, replayed.expected, binding, references)

    warnings = [f"stage 5 dropped: {reason}" for reason in rejected]
    if stale:
        warnings.append(
            "the task's own work invalidates: "
            + ", ".join(f"{s} ({references[s]['phrase']!r})" for s in sorted(stale))
        )

    # Each rung rewrites the rung below — its text AND its judge specification, because an item
    # written against v1 names steps and ids that the rung above has removed.
    prompts = {"1": v1}
    judges = {"1": judge}
    for level in LEVELS[1:]:
        previous = LEVELS[LEVELS.index(level) - 1]
        text, restated, complaints = rewrite_prompt(
            author, level, spec, sequence, adapter, seed, binding, references, plan,
            prompts[previous], judges[previous], stale, context,
        )
        prompts[level], judges[level] = text, restated
        warnings += [f"v{level}: {complaint}" for complaint in complaints]
    # Authored content quoting a phrase a reference depends on is not fatal — references are
    # resolved against the seed, and the agent reads before it writes — but it means the
    # description stops being unique partway through the rollout, so it is worth recording.
    for symbol, reference in references.items():
        phrase = str(reference["params"].get("text", "")).casefold()
        if phrase and any(phrase in text.casefold() for text in content.values()):
            warnings.append(
                f"authored content repeats the phrase {reference['phrase']!r}"
            )

    return TaskRecord(
        task_id=sequence.task_id,
        idx=idx,
        topic=populated.topic,
        seed=seed.model_dump(),
        expected=replayed.expected.model_dump(),
        prompts=prompts,
        judge=judges,
        steps=[asdict(step) for step in sequence.steps],
        manifest=[asdict(entry) for entry in sequence.manifest],
        slots=[asdict(slot) for slot in sequence.slots],
        binding=replayed.binding,
        references=references,
        content=content,
        observed=replayed.observed,
        args=replayed.args,
        step_deltas=replayed.step_deltas,
        turn_diffs=replayed.turn_diffs,
        expected_facts=expected_facts(adapter, seed, replayed.expected),
        shape=sequence.shape,
        warnings=warnings,
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="my_env2.pipeline")
    parser.add_argument("--num", type=int, default=5)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument(
        "--model",
        default="openai/gpt-5-mini",
        help="use openai/gpt-5-nano while iterating; gpt-5-mini for keepers",
    )
    parser.add_argument("--out", default="tmp/tasks_v2.jsonl")
    parser.add_argument("--cache", default="tmp/my_env2_cache")
    args = parser.parse_args()

    spec = json.loads(SPEC_PATH.read_text())
    author = Author(model=args.model, cache_dir=args.cache)
    adapter = ChatAdapter()

    rows, dropped = [], []
    for idx in range(args.start, args.start + args.num):
        try:
            record = build_task(spec, idx, author, adapter=adapter)
        except Exception as error:  # noqa: BLE001
            # Deliberately everything. A model reply is arbitrary JSON, so a stage can fail in
            # ways no exception type predicts; letting one escape would abandon every task
            # already built, since the file is written after the loop.
            dropped.append((idx, f"{type(error).__name__}: {error}"))
            print(f"idx {idx}: dropped — {type(error).__name__}: {error}", flush=True)
            continue
        rows.append(asdict(record))
        print(
            f"idx {idx}: {record.shape['steps']} steps, "
            f"{len(record.judge['1'])} judge item(s), "
            f"{len(record.references)} reference(s), "
            f"prompts {'/'.join(str(len(p)) for p in record.prompts.values())} chars"
            + (f", {len(record.warnings)} warning(s)" if record.warnings else "")
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
    )
    print(
        f"wrote {out} ({len(rows)} task(s); {len(dropped)} dropped) — "
        f"{author.calls} model call(s), {author.cache_hits} from cache"
    )


if __name__ == "__main__":
    main()
