"""Did the rewrite-stage changes work? Compare two task files on the three measured defects.

    uv run --with-editable environments/my_env2 \
        python environments/my_env2/review/measure_fixes.py \
            --before environments/my_env2/samples/tasks.jsonl \
            --after  environments/my_env2/review/03_live/tasks.jsonl

The three defects, all of them counted rather than asserted:

1. **A description pasted more than once.** It should introduce a thing at first mention and be
   referred back to afterwards. Before the change, 40 of 81 phrase uses were repeats.
2. **A judge item still speaking the rung below's language** — an entity id, a tool name, or a
   step number in a restated `expected` or `hint`. Those items were shipped unchanged to every
   level, so a grader reading an L3 rollout was checking a task nobody was given.
3. **Sequencing connectives at the goal-level rungs** (`; `, ` then `), which the L3 and L4
   instructions forbid and nothing used to check.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from my_env2.adapter import ChatAdapter  # noqa: E402
from my_env2.pipeline import SPEC_PATH  # noqa: E402
from my_env2.prompts import _forbidden, _judge_leaks, stale_references  # noqa: E402
from my_env2.state import ChatState  # noqa: E402


def judge_at(row: dict, level: str) -> list[dict]:
    judge = row.get("judge") or []
    if isinstance(judge, dict):
        return judge.get(level) or judge.get("1") or []
    return judge


def measure(path: Path, spec: dict, adapter: ChatAdapter) -> dict:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    stats = {
        "tasks": len(rows),
        "levels": sorted({lvl for row in rows for lvl in row["prompts"]}),
        "phrase_uses": Counter(),
        "phrase_repeats": Counter(),
        "phrase_zero": Counter(),
        "worst_repeat": 0,
        "judge_items": Counter(),
        "judge_leaking": Counter(),
        "leak_kinds": Counter(),
        "sequencing": Counter(),
        "stale_tasks": [],
        "detail": [],
    }
    for row in rows:
        seed = ChatState.model_validate(row["seed"])
        expected = ChatState.model_validate(row["expected"])
        binding, references = row["binding"], row["references"]
        forbidden = _forbidden(spec, adapter, seed, binding, references)
        if stale_references(adapter, expected, binding, references):
            stats["stale_tasks"].append(row["task_id"])

        for level, prompt in row["prompts"].items():
            if level == "1":
                continue  # the explicit rung names ids on purpose
            for reference in references.values():
                count = prompt.count(reference["phrase"])
                stats["phrase_uses"][level] += 1
                if count > 1:
                    stats["phrase_repeats"][level] += 1
                    stats["worst_repeat"] = max(stats["worst_repeat"], count)
                    stats["detail"].append(
                        f"{row['task_id']} v{level}: {count}x {reference['phrase'][:52]!r}"
                    )
                elif count == 0:
                    stats["phrase_zero"][level] += 1
            if level in ("3", "4"):
                stats["sequencing"][level] += len(
                    re.findall(r"(?i)\b(?:and )?then\b|;\s", prompt)
                )
            for item in judge_at(row, level):
                stats["judge_items"][level] += 1
                leaks = _judge_leaks(item, forbidden)
                if leaks:
                    stats["judge_leaking"][level] += 1
                    for leak in leaks:
                        stats["leak_kinds"][
                            "step number" if "step" in leak else "id or tool name"
                        ] += 1
    return stats


def show(label: str, stats: dict) -> None:
    levels = [lvl for lvl in stats["levels"] if lvl != "1"]
    print(f"\n=== {label}: {stats['tasks']} tasks, levels {'/'.join(stats['levels'])}")
    uses = sum(stats["phrase_uses"].values())
    repeats = sum(stats["phrase_repeats"].values())
    zeros = sum(stats["phrase_zero"].values())
    print(f"  descriptions        {uses} uses across the de-scaffolded rungs")
    print(f"    pasted >1 time    {repeats}"
          + (f"   (worst: {stats['worst_repeat']}x in one prompt)" if repeats else ""))
    print(f"    never used        {zeros}")
    items = sum(stats["judge_items"].values())
    leaking = sum(stats["judge_leaking"].values())
    print(f"  judge items         {items} across those rungs")
    print(f"    still speak v1    {leaking}"
          + (f"   ({dict(stats['leak_kinds'])})" if leaking else ""))
    print("  sequencing          " + (
        ", ".join(f"v{lvl}: {stats['sequencing'][lvl]}" for lvl in levels if lvl in ("3", "4"))
        or "n/a"))
    print(f"  self-invalidating   {stats['stale_tasks'] or 'none'}")
    for line in stats["detail"][:8]:
        print(f"    - {line}")
    if len(stats["detail"]) > 8:
        print(f"    … and {len(stats['detail']) - 8} more")


def main() -> None:
    parser = argparse.ArgumentParser(prog="measure_fixes")
    parser.add_argument("--before", default=str(HERE.parent / "samples" / "tasks.jsonl"))
    parser.add_argument("--after", default=str(HERE / "03_live" / "tasks.jsonl"))
    args = parser.parse_args()

    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    adapter = ChatAdapter()
    for label, path in (("BEFORE", Path(args.before)), ("AFTER", Path(args.after))):
        if not path.exists():
            print(f"\n=== {label}: {path} does not exist")
            continue
        show(f"{label}  ({path})", measure(path, spec, adapter))


if __name__ == "__main__":
    main()
