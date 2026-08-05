"""Inspecting the pipeline without running it.

python -m my_env2.cli plan --idx 3          # the symbolic sequence, offline
python -m my_env2.cli world --idx 3         # what a mechanical world would look like
python -m my_env2.cli task --idx 3          # a persisted task, end to end
python -m my_env2.cli result <run dir>      # rewards from a finished eval
"""

import argparse
import json
import random
from pathlib import Path

from my_env2.adapter import ChatAdapter
from my_env2.pipeline import DEFAULT_CONFIGS, SPEC_PATH
from my_env2.render import manifest_brief, symbolic_steps
from my_env2.symbolic import generate_sequence


def _sequence(idx: int):
    spec = json.loads(SPEC_PATH.read_text())
    return spec, generate_sequence(
        spec, random.Random(idx), DEFAULT_CONFIGS, task_id=f"t{idx}"
    )


def cmd_plan(args) -> None:
    spec, sequence = _sequence(args.idx)
    print(f"=== SYMBOLIC SEQUENCE  idx={args.idx} ===")
    print(symbolic_steps(spec, sequence))
    print("\n=== ENTITIES THE WORLD MUST SUPPLY ===")
    print(manifest_brief(sequence) or "  (none)")
    print("\n=== SLOTS THE AUTHORING PASS MUST FILL ===")
    for slot in sequence.slots:
        where = f" <- {', '.join(slot.sources)}" if slot.sources else ""
        print(f"  [{slot.kind:7}] step {sequence.number(slot.key)} {slot.param}{where}")
    print("\n=== REALIZED SHAPE ===")
    print(json.dumps(sequence.shape, indent=1))


def cmd_world(args) -> None:
    """The deterministic stand-in for Stage 3, so the spine can be read without a model."""
    from my_env2.replay import replay
    from my_env2.seed import build, summarise
    from tests.stub import stub_world

    spec, sequence = _sequence(args.idx)
    required = {
        e.symbol: e.entity_type for e in sequence.manifest if e.origin == "seed"
    }
    seed, binding = build(stub_world(sequence), required)
    adapter = ChatAdapter()
    print(summarise(seed))
    print("\n=== BINDING ===")
    replayed = replay(spec, sequence, adapter, seed, binding)
    for symbol, entity_id in replayed.binding.items():
        print(f"  {symbol:14} -> {entity_id}")
    print("\n=== WHAT THE REWARD WILL LOOK FOR ===")
    for turn in replayed.turn_diffs:
        print(f"  turn {turn['turn']}:")
        for fact in turn["added"]:
            print(f"      {fact}")


def cmd_task(args) -> None:
    rows = [
        json.loads(line)
        for line in Path(args.dataset).read_text().splitlines()
        if line.strip()
    ]
    row = next((r for r in rows if r["idx"] == args.idx), rows[0])
    print(f"=== TASK {row['task_id']} — {row['topic']} ===")
    print(f"shape: {json.dumps(row['shape'])}")
    if row["warnings"]:
        print("\nWARNINGS")
        for warning in row["warnings"]:
            print(f"  - {warning}")
    print("\n=== HOW THINGS ARE REFERRED TO ===")
    for symbol, reference in row["references"].items():
        print(f"  {symbol:14} {row['binding'][symbol]:12} {reference['mode']}")
        print(f"      {reference['phrase']}")
    print("\n=== JUDGE SPECIFICATION ===")
    for item in row["judge"]:
        print(f"  {item['id']}")
        print(f"      requirement: {item['requirement']}")
        print(f"      expected   : {item['expected']}")
        print(f"      where      : {item['hint']}")
    print("\n=== WHAT THE STATE REWARD LOOKS FOR ===")
    for fact in row["expected_facts"]:
        print(f"  {fact}")
    for level in ("1", "2", "3"):
        print(f"\n===== PROMPT v{level} ({len(row['prompts'][level])} chars) =====")
        print(row["prompts"][level])


def cmd_result(args) -> None:
    path = Path(args.run) / "traces.jsonl"
    if not path.exists():
        raise SystemExit(f"no traces.jsonl under {args.run}")
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        trace = json.loads(line)["traces"][0]
        rewards = trace["rewards"]
        total = sum(value["score"] * value["weight"] for value in rewards.values())
        print(f"=== task idx {trace['task']['data']['idx']} — total {total:.3f} ===")
        for key, value in sorted(rewards.items()):
            print(f"    {key:12} {value['score']:.3f}  (weight {value['weight']})")
        results = {
            node["message"]["tool_call_id"]: node["message"].get("content")
            for node in trace["nodes"]
            if node["message"].get("role") == "tool"
        }
        print("    calls:")
        for node in trace["nodes"]:
            for call in node["message"].get("tool_calls") or []:
                failed = '"error"' in str(results.get(call["id"], ""))
                print(
                    f"      {'x' if failed else '+'} {call['name']:24} {call['arguments'][:64]}"
                )


def main() -> None:
    parser = argparse.ArgumentParser(prog="my_env2.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    plan = sub.add_parser(
        "plan", help="print the symbolic sequence for an index (offline)"
    )
    plan.add_argument("--idx", type=int, default=0)
    plan.set_defaults(func=cmd_plan)

    world = sub.add_parser(
        "world", help="build a mechanical world for it and replay (offline)"
    )
    world.add_argument("--idx", type=int, default=0)
    world.set_defaults(func=cmd_world)

    task = sub.add_parser("task", help="print an authored task from a dataset")
    task.add_argument("--idx", type=int, default=0)
    task.add_argument("--dataset", default="tmp/tasks_v2.jsonl")
    task.set_defaults(func=cmd_task)

    result = sub.add_parser(
        "result", help="print rewards + tool calls from a finished run"
    )
    result.add_argument("run")
    result.set_defaults(func=cmd_result)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
