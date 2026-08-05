"""Per-level breakdown of how each rung uses its reference descriptions, and of sequencing.

The aggregate in `measure_fixes.py` hides the thing that matters: L4 is *allowed* to render a
description in natural English, so a zero count there is intended, while a zero count at L2 or L3
means the rung dropped a reference it was told to use.

    uv run --with-editable environments/my_env2 \
        python environments/my_env2/review/per_level.py FILE [FILE ...]
"""

import json
import re
import sys
from pathlib import Path


def report(path: Path) -> None:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"--- {path.name}  ({len(rows)} tasks)")
    print("     lvl   refs   used-1x    >1x     0x    seq")
    for level in ("2", "3", "4"):
        if not any(level in row["prompts"] for row in rows):
            continue
        one = multi = zero = seq = 0
        for row in rows:
            prompt = row["prompts"].get(level)
            if prompt is None:
                continue
            seq += len(re.findall(r"(?i)\b(?:and )?then\b|;\s", prompt))
            for reference in row["references"].values():
                count = prompt.count(reference["phrase"])
                one += count == 1
                multi += count > 1
                zero += count == 0
        print(f"     {level:>3} {one + multi + zero:>6} {one:>9} {multi:>6} {zero:>6} {seq:>6}")
    print()


if __name__ == "__main__":
    for argument in sys.argv[1:]:
        report(Path(argument))
