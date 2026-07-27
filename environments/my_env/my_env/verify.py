"""Verification of a rollout.

Two independent passes, meant to be composed by the final verifier:

- `score` (state pass): F1 agreement between the expected and actual final state,
  reduced to id/structure facts via `adapter.signature` (content excluded). Missing
  expected changes lower recall; unexpected changes lower precision.
- `tool_call_score` (trace pass): fraction of the agent's tool calls that are
  well-formed against the spec's parameter schema — penalizes malformed calls (missing
  required params, unknown params, unknown tool, unparseable arguments).
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


def score(seed, expected, trace, adapter) -> float:
    baseline = adapter.signature(seed)
    delta_expected = adapter.signature(expected) - baseline
    delta_actual = adapter.signature(trace.state) - baseline
    return _f1(delta_expected, delta_actual)


def _tool_calls(trace) -> list[tuple[str, dict | None]]:
    """Every tool call in the trace as (name, parsed_args); args is None if unparseable."""
    calls = []
    for node in trace.nodes:
        message = node.message
        if message.role == "assistant" and message.tool_calls:
            for call in message.tool_calls:
                try:
                    args = json.loads(call.arguments or "{}")
                except json.JSONDecodeError:
                    args = None
                calls.append((call.name, args))
    return calls


def _call_is_wellformed(name: str, args: dict | None, params_by_tool: dict) -> bool:
    if name not in params_by_tool:
        return False  # unknown tool
    if args is None:
        return False  # unparseable arguments
    declared = {p["name"] for p in params_by_tool[name]}
    required = {p["name"] for p in params_by_tool[name] if p.get("required")}
    return required <= set(args) <= declared  # no missing required, no unknown params


def tool_call_score(trace, spec: dict) -> float:
    """Fraction of the agent's tool calls that are well-formed against `spec`'s parameter
    schema. 1.0 when no calls were made (this pass judges well-formedness only; coverage
    is the state pass's job)."""
    params_by_tool = {a["tool"]: a["params"] for a in spec["actions"]}
    calls = _tool_calls(trace)
    if not calls:
        return 1.0
    wellformed = sum(_call_is_wellformed(n, a, params_by_tool) for n, a in calls)
    return wellformed / len(calls)


# --- judge pass: LLM-graded open-ended answers (one call per task) ---

_OPEN_ENDED_PROMPT = """You grade an agent's answers to open-ended sub-questions.

For each numbered item you are given the question, the correct (gold) answer, and a hint
for where the agent's answer should appear in its output. Decide whether the agent's
output contains a correct answer — matching the gold in substance (exact wording may
differ). Judge correctness only, not style.

The agent's output has two parts. Grade against the DELIVERED OUTPUT section only: an
answer that appears in a tool result but that the agent never delivered where the hint
says does NOT count as correct. The FULL ROLLOUT section is context — use it to tell a
genuinely retrieved answer from a guess, never as the answer itself.

Items:
{items}

Agent output:
{transcript}

Respond with ONLY a JSON array of booleans, one per item in order (true = correct).
Example for two items: [true, false]"""


class OpenEndedJudge(vf.Judge[list, vf.JudgeConfig]):
    prompt = _OPEN_ENDED_PROMPT

    def parse(self, response):
        text = response.text
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end == -1:
            raise ValueError(f"judge did not return a JSON array: {text[:200]!r}")
        return [bool(x) for x in json.loads(text[start : end + 1])]


def _render_items(items: list[dict]) -> str:
    return "\n".join(
        f"{i}. Question: {item['question']}\n"
        f"   Gold answer: {item['ground_truth']}\n"
        f"   Where to look: {item['judge_hint']}"
        for i, item in enumerate(items, 1)
    )


async def judge_open_ended(items: list[dict], transcript: str, config, trace=None) -> float:
    """One judge call scoring the fraction of open-ended items answered correctly.
    1.0 when there are no items (nothing to judge)."""
    if not items:
        return 1.0
    response = await OpenEndedJudge(config).evaluate(
        trace=trace, items=_render_items(items), transcript=transcript
    )
    verdicts = response.parsed or []
    n = len(items)
    return sum(1 for i in range(n) if i < len(verdicts) and verdicts[i]) / n
