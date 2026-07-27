"""Author natural-language tasks from generated scaffolds — a one-time, LLM-backed step.

Runs the deterministic `generate` for N scaffolds, asks an LLM to turn each into a
single moderate-ambiguity task prompt plus concretized open-ended DeepWiki items
(question + gold answer + a hint for where the judge should look), and writes
`authored_tasks.jsonl`. It is nondeterministic and LLM-costed, so run it once and treat
the JSONL as the frozen, reusable artifact.

    uv run python -m my_env.author --num 5
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
- Refer to chats/messages/users by natural descriptions ("the launch channel", "Alice's \
latest message", "Bob"), NOT by raw ids like c_001 or m_003.
- Keep the intended actions UNIQUELY recoverable — harder to parse, not underspecified. A \
careful agent should be able to reconstruct exactly the listed actions, in order.
- Cover every step, in order.

For each [open-ended] DeepWiki step, YOU choose a real GitHub repo and a specific question \
(language, authors, license, purpose, stars — anything) and weave the request naturally \
into the task. IMPORTANT: the agent sees ONLY your `prompt` text — it never sees the list \
below — so embed the full repo name and the exact question directly in the prompt. Never \
write "see the open-ended step below" or refer to a separate list. Then record for it:
- question: the exact question you embedded in the prompt,
- ground_truth: the correct answer (your best knowledge),
- judge_hint: where in the agent's output the answer should appear (e.g. "in the message \
the agent sends to the launch channel" or "in the agent's final reply").

Respond with ONLY a JSON object, no prose or code fences:
{"prompt": "<the task text>", "open_ended": [{"question": "...", "ground_truth": "...", "judge_hint": "..."}]}
Use an empty list if there are no open-ended steps."""


def _describe(step: dict) -> str:
    if step.get("open_ended"):
        return f"[open-ended] {step['tool']}: you choose the repo + question, and supply the gold answer + judge hint"
    desc = f"{step['tool']}({json.dumps(step['args'])})"
    if step["kind"] == "invalid":
        desc += "  — targets a nonexistent entity; include it as a normal instruction (the agent will attempt it and it will fail)"
    return desc


def _render_plan(seed, timeline) -> str:
    lines = [f"APP STATE (you act as {seed.users['u_me'].name}, id u_me):"]
    lines.append("Users: " + ", ".join(f"{u.name} ({uid})" for uid, u in seed.users.items()))
    for cid, chat in seed.chats.items():
        members = ", ".join(seed.users[m].name for m in chat.member_ids if m in seed.users)
        lines.append(f"Chat '{chat.name or cid}' ({cid}) — members: {members}")
        for message in (m for m in seed.messages if m.chat_id == cid):
            lines.append(f"  {message.id} [{seed.users[message.sender_id].name}]: {message.text}")
    lines.append("\nACTION PLAN (perform in order):")
    step_number = 1
    for group in timeline:
        for step in group:
            lines.append(f"  {step_number}. {_describe(step)}")
            step_number += 1
    return "\n".join(lines)


def _parse(text: str) -> dict:
    # Tolerate stray prose / code fences: take the outermost JSON object.
    start, end = text.find("{"), text.rfind("}")
    data = json.loads(text[start : end + 1])
    return {"prompt": data["prompt"], "open_ended": data.get("open_ended", [])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num", type=int, default=5)
    parser.add_argument("--out", default=str(Path(__file__).parent / "authored_tasks.jsonl"))
    parser.add_argument("--model", default="openai/gpt-5-mini")
    parser.add_argument("--timesteps", type=int, default=3)
    parser.add_argument("--max-actions", type=int, default=3)
    parser.add_argument("--p-invalid", type=float, default=0.2)
    parser.add_argument("--p-open", type=float, default=0.3)
    args = parser.parse_args()

    base_url, api_key = os.environ.get("OPENROUTER_BASE_URL"), os.environ.get("OPENROUTER_API_KEY")
    if not base_url or not api_key:
        raise SystemExit("set OPENROUTER_BASE_URL and OPENROUTER_API_KEY in the environment")
    client = OpenAI(base_url=base_url, api_key=api_key)

    adapter = ChatAdapter()
    action_ids = [a["id"] for a in _SPEC["actions"]]

    rows = []
    for idx in range(args.num):
        seed, expected, timeline = generate(
            _SPEC, adapter, action_ids, args.timesteps, args.max_actions, args.p_invalid, args.p_open, idx
        )
        response = client.chat.completions.create(
            model=args.model,
            temperature=0.7,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": _render_plan(seed, timeline)},
            ],
        )
        authored = _parse(response.choices[0].message.content or "")
        rows.append(
            {
                "idx": idx,
                "seed": seed.model_dump(),
                "expected": expected.model_dump(),
                "steps": [step for group in timeline for step in group],
                "prompt": authored["prompt"],
                "open_ended": authored["open_ended"],
            }
        )
        print(f"authored idx {idx}: {len(authored['open_ended'])} open item(s)")

    Path(args.out).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"wrote {args.out} ({len(rows)} tasks)")


if __name__ == "__main__":
    main()
