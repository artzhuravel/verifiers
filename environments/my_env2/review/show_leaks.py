"""Which restated judge items still speak a lower rung's language, and how.

    uv run --with-editable environments/my_env2 \
        python environments/my_env2/review/show_leaks.py [FILE]
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from my_env2.adapter import ChatAdapter  # noqa: E402
from my_env2.pipeline import SPEC_PATH  # noqa: E402
from my_env2.prompts import _forbidden, _judge_leaks  # noqa: E402
from my_env2.state import ChatState  # noqa: E402


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "03_live" / "tasks.jsonl"
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    adapter = ChatAdapter()
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    total = leaking = 0
    for row in rows:
        seed = ChatState.model_validate(row["seed"])
        forbidden = _forbidden(spec, adapter, seed, row["binding"], row["references"])
        # A pre-per-level file carries one flat list that was served at EVERY level, so to compare
        # fairly it has to be evaluated against each de-scaffolded rung, not skipped.
        judge = (
            row["judge"]
            if isinstance(row["judge"], dict)
            else {level: row["judge"] for level in row["prompts"]}
        )
        for level, items in judge.items():
            if level == "1":
                continue  # the explicit rung is allowed to name ids
            for item in items:
                total += 1
                leaks = _judge_leaks(item, forbidden)
                if not leaks:
                    continue
                leaking += 1
                print(f"{row['task_id']} v{level} {item['id']}: {', '.join(leaks)}")
                print(f"    expected: {item['expected'][:130]}")
                print(f"    hint:     {item['hint'][:130]}")
    print(f"\n{leaking} of {total} restated items still leak")


if __name__ == "__main__":
    main()
