"""Scoring a rollout.

Two components, and the split between them is the pipeline's central claim: everything the
environment represents *structurally* is checked deterministically, and only what it cannot
represent is left to a judge.

- `state_diff` — F1 between the facts a faithful run adds and the facts this run added, via
  `adapter.signature`. Path-agnostic by construction: it compares end states, so any ordering
  that arrives at the right place scores the same. That matters because v3 deliberately stops
  telling the agent what order to work in.
- `judge_score` — the judge specification from Stage 8. Every item is information that had to
  travel from a read into a message or into the agent's reply, which no state comparison can
  see. One call per task, whatever the number of items.
"""

import json

import verifiers.v1 as vf


def _f1(expected: set, actual: set) -> float:
    if not expected and not actual:
        return 1.0  # nothing expected, nothing done -> perfect
    true_positive = len(expected & actual)
    precision = true_positive / len(actual) if actual else 1.0
    recall = true_positive / len(expected) if expected else 1.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def state_diff(seed, expected, trace, adapter) -> float:
    # `seed` is passed to every signature call: it is what tells the adapter which entities
    # pre-existed (and so keep their ids) and which the rollout created.
    baseline = adapter.signature(seed, seed)
    return _f1(
        adapter.signature(expected, seed) - baseline,
        adapter.signature(trace.state, seed) - baseline,
    )


# The per-turn diffs Stage 6 records are deliberately NOT scored. Every fact in them is
# already inside the `state_diff` comparison, and a milestone reward can only ask whether a
# turn's facts are all present — recall with no precision term — so adding it would dilute the
# one half of the F1 that punishes an agent for changing things nobody asked it to change.
# They are persisted, and the CLI prints them, because they are what makes a failed rollout
# readable: they say which turn the run stopped matching at.


# --- judge pass ----------------------------------------------------------------------

_JUDGE_PROMPT = """You grade whether an agent delivered specific pieces of information.

Each numbered item is something the agent had to find out and then put somewhere. You are given \
the requirement, what a correct answer says, and where in the agent's output to look for it. \
Decide whether the agent's output contains a correct answer there — matching in substance, \
wording may differ. Judge correctness only, never style.

The agent's output has two parts. Grade against the DELIVERED OUTPUT section alone: an answer \
sitting in a tool result that the agent never delivered where the hint says does NOT count. The \
FULL ROLLOUT section is context — use it to tell a genuinely retrieved answer from a guess, \
never as the answer itself.

Items:
{items}

Agent output:
{transcript}

Respond with ONLY a JSON array of booleans, one per item in order (true = correct).
Example for two items: [true, false]"""


class DeliveryJudge(vf.Judge[list, vf.JudgeConfig]):
    prompt = _JUDGE_PROMPT

    def parse(self, response):
        text = response.text
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end == -1:
            raise ValueError(f"judge did not return a JSON array: {text[:200]!r}")
        return [bool(value) for value in json.loads(text[start : end + 1])]


def transcript(trace: vf.Trace, seeded: set[str]) -> str:
    """What the judge sees: the whole rollout, then the part that counts for grading.

    The full trace lets the judge tell work from invention — an answer the agent guessed is not
    an answer it retrieved. Grading still targets delivered output only: messages the agent sent
    during this rollout plus its final reply, because every judge item is about delivery.
    Seeded messages are excluded, since the world ships with history the acting user "wrote".
    """
    state = trace.state
    sent = []
    for message in state.messages:
        if message.sender_id == state.me and message.id not in seeded:
            chat = state.chats.get(message.chat_id)
            label = chat.name if chat and chat.name else message.chat_id
            sent.append(f"[{label}] {message.text}")
    return (
        "FULL ROLLOUT — every tool call the agent made and what came back. Context only:\n"
        f"{trace.transcript}\n\n"
        "=== DELIVERED OUTPUT — grade against this section alone ===\n"
        f"Messages the agent sent:\n{chr(10).join(sent) or '(none)'}\n\n"
        f"Agent's final reply:\n{trace.last_reply or ''}"
    )


async def judge_score(items: list[dict], text: str, config, trace=None) -> float:
    """One judge call, scoring the fraction of items delivered. 1.0 when there are none."""
    if not items:
        return 1.0
    rendered = "\n".join(
        f"{number}. {item['requirement']}\n"
        f"   A correct answer says: {item['expected']}\n"
        f"   Where to look: {item['hint']}"
        for number, item in enumerate(items, 1)
    )
    response = await DeliveryJudge(config).evaluate(
        trace=trace, items=rendered, transcript=text
    )
    verdicts = response.parsed
    if len(verdicts) != len(items):
        # Raise rather than count the missing ones wrong. A judge that returned the wrong number
        # of verdicts has failed, and a judge failure is not the agent's to pay for.
        raise ValueError(
            f"judge returned {len(verdicts)} verdict(s) for {len(items)} item(s): {verdicts}"
        )
    return sum(1 for verdict in verdicts if verdict) / len(items)
