"""Put a hand-written L4 through the real checks, so the new instruction can be judged before a
live authoring run is paid for.

The text below is written by hand as a TARGET — what the Stage 11 instruction is asking for. Running
it through `_complaints`, `_judge_leaks` and `stale_references` says whether the target is actually
reachable under the rules, and whether the rules would accept it.

    uv run --with-editable environments/my_env2 \
        python environments/my_env2/review/check_l4_target.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from my_env2.adapter import ChatAdapter  # noqa: E402
from my_env2.pipeline import SPEC_PATH  # noqa: E402
from my_env2.prompts import (  # noqa: E402
    _complaints,
    _forbidden,
    _judge_leaks,
    stale_references,
)
from my_env2.state import ChatState  # noqa: E402

TASK = "t1"

L4 = (
    "There's one conversation I still haven't caught up on — could you clear my unread there and "
    "bring the rest of us up to speed while you're at it? Post a rundown into it of who said what "
    "in the recent traffic, so anyone skimming can see it without scrolling back. Someone in there "
    "asked for a repo's licence to be confirmed, in the message about someone confirm its license "
    "— find out what apache/cassandra is actually for and what it's mostly written in, and put "
    "that under their question. Round it off by following up on your own rundown, offering to run "
    "the same check over any other repos on the checklist and asking which ones they want done."
)

JUDGE = {
    "carry:c0a1:text": {
        "expected": (
            "The rundown posted into that conversation names each person who posted recently and "
            "reproduces what they said — Sam Ortega's heads-up about the security audit and the "
            "need to collect licence, primary language and maintainer lists; Marisa's offer to "
            "check licences; Lina's proposal of apache/cool-db with a request to confirm its "
            "licence, language and maintainers; Raj's note that it is Apache-2.0 and Java; and the "
            "later checklist and maintainer requests."
        ),
        "hint": "the rundown of who said what, posted into the conversation being caught up on",
    },
    "carry:c1a1:text": {
        "expected": (
            "The reply under the message asking for a licence to be confirmed states that "
            "apache/cassandra is a distributed NoSQL database for handling large-scale data with "
            "high availability, and that its primary programming language is Java."
        ),
        "hint": "the reply posted underneath the message that asked for the licence to be confirmed",
    },
}


def main() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    adapter = ChatAdapter()
    rows = {
        json.loads(line)["task_id"]: json.loads(line)
        for line in (HERE.parent / "samples" / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    row = rows[TASK]
    seed = ChatState.model_validate(row["seed"])
    expected = ChatState.model_validate(row["expected"])
    binding, references = row["binding"], row["references"]
    forbidden = _forbidden(spec, adapter, seed, binding, references)
    phrases = [r["phrase"] for r in references.values()]
    stale = stale_references(adapter, expected, binding, references)

    print(f"=== {TASK}: does the hand-written L4 pass the checks the stage applies? ===\n")
    print(f"references the work invalidates: {sorted(stale) or 'none'}")
    for symbol, reference in references.items():
        print(f"  {symbol:12} used {L4.count(reference['phrase'])}x  \"{reference['phrase']}\"")
    print()

    complaints = _complaints(L4, forbidden, phrases, flag_sequencing=True)
    print("PROMPT COMPLAINTS")
    print("\n".join(f"  - {c}" for c in complaints) or "  (none)")
    print()

    print("JUDGE ITEM COMPLAINTS — the restated items")
    any_leak = False
    for item_id, restated in JUDGE.items():
        leaks = _judge_leaks({**restated, "id": item_id}, forbidden)
        any_leak = any_leak or bool(leaks)
        print(f"  {item_id}: " + (", ".join(leaks) if leaks else "clean"))
    print()

    print("THE SAME CHECKS ON WHAT SHIPPED (the pre-fix L3 and its judge items)")
    shipped = _complaints(row["prompts"]["3"], forbidden, phrases, flag_sequencing=True)
    print("  prompt:")
    print("\n".join(f"    - {c}" for c in shipped) or "    (none)")
    print("  judge items:")
    for item in row["judge"]:
        leaks = _judge_leaks(item, forbidden)
        print(f"    {item['id']}: " + (", ".join(leaks) if leaks else "clean"))

    print()
    print("VERDICT:", "the target passes" if not complaints and not any_leak
          else "the target does NOT pass — see above")


if __name__ == "__main__":
    main()
