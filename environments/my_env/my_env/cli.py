"""Small CLI for inspecting the pipeline: show a sampled plan, the authored prompts, or a
finished run's scores. Defaults match the `./tasks` preset, so every subcommand runs bare.

    python -m my_env.cli plan
    python -m my_env.cli prompts
    python -m my_env.cli result
"""

import argparse
import json
from pathlib import Path

from my_env.adapter import ChatAdapter
from my_env.generate import generate

SPEC_PATH = Path(__file__).parent / "action_spec.json"
# The default preset, mirrored in `./tasks`. `author.py` must be given the same values
# to re-derive this plan.
PRESET = {"timesteps": 3, "max_actions": 2, "p_invalid": 0.25, "p_open": 0.3}


def cmd_plan(args) -> None:
    spec = json.loads(SPEC_PATH.read_text())
    adapter = ChatAdapter()
    seed, expected, timeline = generate(
        spec,
        adapter,
        [a["id"] for a in spec["actions"]],
        args.timesteps,
        args.max_actions,
        args.p_invalid,
        args.p_open,
        args.idx,
    )
    print(
        f"=== SAMPLED PLAN  idx={args.idx}  timesteps={args.timesteps} "
        f"max_actions={args.max_actions} p_invalid={args.p_invalid} p_open={args.p_open} ==="
    )
    n = 0
    for step_number, group in enumerate(timeline, 1):
        print(f"timestep {step_number}:")
        for step in group:
            n += 1
            tag = "OPEN" if step["open_ended"] else step["kind"].upper()
            print(f'  {n}. [{tag:7}] {step["tool"]:24} {json.dumps(step["args"])}')
    print("\n=== EXPECTED STATE CHANGE (what the reward checks) ===")
    delta = adapter.signature(expected, seed) - adapter.signature(seed, seed)
    for fact in sorted(map(str, delta)):
        print("  ", fact)
    if args.world:
        print(f"\n=== SEED WORLD: {len(seed.users)} users, {len(seed.chats)} chats, "
              f"{len(seed.messages)} messages ===")
        for chat in seed.chats.values():
            print(f'  {chat.id}  {chat.kind:5} {chat.name or "(dm)"}')
    if args.save:
        # Persist the plan so the authoring step consumes exactly this task rather than
        # re-deriving it from the sampling knobs.
        out = Path(args.save)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {
                    "idx": args.idx,
                    "seed": seed.model_dump(),
                    "expected": expected.model_dump(),
                    "timeline": timeline,
                }
            )
        )
        print(f"\nsaved plan -> {out}")


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def cmd_prompts(args) -> None:
    directory = Path(args.dir)
    files = sorted(directory.glob("authored_tasks_l*.jsonl"))
    if not files:
        raise SystemExit(f"no authored_tasks_l*.jsonl in {directory}")
    for path in files:
        rows = _rows(path)
        row = next((r for r in rows if r["idx"] == args.idx), rows[0])
        print(f"\n===== {path.stem.rsplit('_', 1)[-1].upper()}  ({len(row['prompt'])} chars) =====")
        print(row["prompt"])
    print("\n===== OPEN-ENDED GOLDS (the judge's ground truth) =====")
    for item in row["open_ended"]:
        print(f"  Q     : {item['question']}")
        print(f"  gold  : {item['ground_truth']}")
        print(f"  where : {item['judge_hint']}\n")


def cmd_result(args) -> None:
    path = Path(args.run) / "traces.jsonl"
    if not path.exists():
        raise SystemExit(f"no traces.jsonl under {args.run}")
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        trace = json.loads(line)["traces"][0]
        rewards = trace["rewards"]
        total = sum(v["score"] * v["weight"] for v in rewards.values())
        print(f"=== task idx {trace['task']['data']['idx']} — total {total:.3f} ===")
        for key, value in sorted(rewards.items()):
            print(f"    {key:12} {value['score']:.3f}  (weight {value['weight']})")
        results = {
            n["message"]["tool_call_id"]: n["message"].get("content")
            for n in trace["nodes"]
            if n["message"].get("role") == "tool"
        }
        print("    calls:")
        for node in trace["nodes"]:
            for call in node["message"].get("tool_calls") or []:
                failed = '"error"' in str(results.get(call["id"], ""))
                print(f'      {"x" if failed else "+"} {call["name"]:24} {call["arguments"][:64]}')


def main() -> None:
    parser = argparse.ArgumentParser(prog="my_env.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    plan = sub.add_parser("plan", help="sample and print an action plan (offline)")
    plan.add_argument("--idx", type=int, default=0)
    plan.add_argument("--timesteps", type=int, default=PRESET["timesteps"])
    plan.add_argument("--max-actions", type=int, default=PRESET["max_actions"])
    plan.add_argument("--p-invalid", type=float, default=PRESET["p_invalid"])
    plan.add_argument("--p-open", type=float, default=PRESET["p_open"])
    plan.add_argument("--world", action="store_true", help="also summarise the seed world")
    plan.add_argument("--save", help="write the plan to this path for `author --plan`")
    plan.set_defaults(func=cmd_plan)

    prompts = sub.add_parser("prompts", help="print the authored prompt at every rung")
    prompts.add_argument("dir", nargs="?", default="tmp/tasks")
    prompts.add_argument("--idx", type=int, default=0)
    prompts.set_defaults(func=cmd_prompts)

    result = sub.add_parser("result", help="print rewards + tool calls from a finished run")
    result.add_argument("run", nargs="?", default="outputs/my_env--openai--gpt-5-nano--null/l3")
    result.set_defaults(func=cmd_result)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
