# my_env — a generated tool-use environment (overview & handoff)

This is a working, end-to-end pipeline for **automatically generating verifiable,
multi-step tool-use tasks** for an LLM agent, and scoring them with a composite verifier.
It doubles as a reusable *pattern* for building generated-task environments: the
generator and scoring core are environment-agnostic (driven by a spec + an adapter), so
only the chat-specific pieces are bespoke.

Read this first, then `DESIGN.md` for the generator/verifier internals.

## What we're trying to achieve

Produce **lots of tasks, cheaply, with trustworthy rewards**, where:

- tasks exercise a realistic tool surface — a mock chat app (fully controlled, local)
  plus a real read-only web tool (**DeepWiki**, GitHub-repo Q&A over MCP);
- each task is a **deterministically sampled action plan** ("scaffold") turned into a
  **natural-language prompt** by an LLM, at a controllable difficulty (currently one
  *moderate ambiguity* level: natural references instead of raw ids, but the intended
  actions stay uniquely recoverable);
- scoring combines **deterministic** signals (did the world end up as intended; were the
  tool calls well-formed) with an **LLM judge** for the open-ended web answers.

The design intentionally separates *plumbing* (deterministic, verified by state/schema)
from *semantics* (content, verified by a judge). Content is never enforced by the
deterministic passes — only entity **ids / structure** are.

## The pipeline

```
generate (deterministic)  →  author.py (LLM, once)  →  authored_tasks.jsonl  →  human verify  →  eval
   seed + expected +           one NL prompt +            frozen dataset            check golds     3 rewards
   timeline (action plan)      open-ended golds
```

- **generate** — a random walk over the action spec, using the real tools to advance an
  in-memory state (so created-entity ids are deterministic and validity is exact).
  Returns `(seed, expected_final_state, timeline)`. Open-ended DeepWiki actions are
  emitted as empty **placeholder slots** (no API call at gen time).
- **author.py** — a one-time LLM step: turns each scaffold into a single moderate-ambiguity
  **self-contained** prompt and, for each open slot, a `{question, ground_truth, judge_hint}`.
  Output is `authored_tasks.jsonl`, the frozen, reusable artifact.
- **human verify** — a person checks the LLM-authored gold answers are actually true
  (tracked manually; there is deliberately **no `verified` flag** in the schema).
- **eval** — the taskset loads the dataset and scores each task with three rewards.

## Scoring (three weighted rewards on `GeneratedTask`)

| reward | weight | what it measures | how |
|---|---|---|---|
| `state_diff` | 0.5 | did the chat end up as intended | F1 of expected vs actual `trace.state` as id/structure facts (`adapter.signature`); missing → ↓recall, extra → ↓precision. Content excluded. |
| `tool_calls` | 0.2 | were the calls well-formed | fraction of calls valid against the spec's `params`/`required` (`verify.tool_call_score`) |
| `open_ended` | 0.3 | were the DeepWiki answers correct | ONE LLM-judge call/task grading answers vs golds via `judge_hint` (`verify.judge_open_ended`); 1.0 if no open items |

Both deterministic passes were verified to *discriminate* (faithful → 1.0; missing/extra/
malformed → lower), and the judge too (all-right 1.0, one-wrong 0.5, all-wrong 0.0). A
competent agent on well-authored tasks earns ~1.0 across all three.

## Current state — done & verified end-to-end

- Chat app: `state.py` (schema + deterministic id counters), `servers/tool.py`
  (`ChatToolset`: 3 read + 5 write tools), `servers/web.py` (`DeepWikiToolset`, remote).
- `action_spec.json` — the machine-readable contract (11 actions: params/required,
  preconditions with `enforced`, effects, `address.server`). Source of truth for both the
  generator and the tool-call verifier.
- Env-agnostic generator (`generate.py`) + the chat adapter (`adapter.py`).
- Verifier (`verify.py`): `score` (state F1), `tool_call_score`, `judge_open_ended`.
- Authoring (`author.py`) + dataset-load path in `taskset.py`.
- All three rewards wired and validated on a live OpenRouter run.

## File map

| file | role |
|---|---|
| `state.py` | schema: `User`/`Message`/`Chat` + `ChatState` + a fixed `SAMPLE` + id counters |
| `servers/tool.py` | `ChatToolset` — local chat tools on `self.state` |
| `servers/web.py` | `DeepWikiToolset` — remote read-only GitHub Q&A |
| `action_spec.json` | machine-readable action contract (generator + tool-call verifier read it) |
| `generate.py` | **env-agnostic** scaffold generator (spec + adapter → seed/expected/timeline) |
| `adapter.py` | `ChatAdapter` — the env seam (`initial_state`/`objects_of_type`/`invalid_ref`/`apply`/`signature`) |
| `verify.py` | the three scoring passes (generic; env specifics come from the adapter/spec) |
| `author.py` | one-time LLM authoring step → `authored_tasks.jsonl` |
| `taskset.py` | env layer: config, `load()` (live vs dataset), the three `@vf.reward`s |
| `authored_tasks.jsonl` | the frozen authored dataset (3 example tasks) |
| `sample_output.json` | inspection artifact: raw `generate` output (seed/expected/timeline) |
| `legacy_tasksets.py` | hand-written demo tasks (reference; **not loaded**) |
| `DESIGN.md` | generator/adapter/verifier internals |

## How to run

Install once and set OpenRouter creds (agent + judge both use them):

```bash
uv pip install -e environments/my_env
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
export OPENROUTER_API_KEY=...
```

Author a batch, then eval the frozen dataset:

```bash
uv run python -m my_env.author --num 10 --p-open 0.3        # one-time, LLM-costed
uv run eval my_env \
  --env.taskset.dataset environments/my_env/my_env/authored_tasks.jsonl \
  --env.agent.harness.id null -m openai/gpt-5-nano \
  --client.base_url "$OPENROUTER_BASE_URL" --client.api_key_var OPENROUTER_API_KEY --no-push
```

Quick, no-authoring iteration on scaffolds (open-ended items ungraded, prompts are a
stopgap): `uv run eval my_env ...` **without** `--env.taskset.dataset`.

Config knobs — taskset: `dataset`, `num_generated`, `timesteps`, `max_actions_per_t`,
`p_invalid`, `p_open`; per-task: `tools`, `web` (DeepWiki url), `judge` (judge endpoint/model).

## Key decisions & lessons (don't relearn these)

- **Ids/structure enforced, content deferred.** The state-diff never checks text/emoji/
  names — only ids and structural facts. Content correctness is the judge's job.
- **State-diff over trace-matching (Option B).** The reward compares expected vs actual
  final state (F1), which naturally penalizes *extra* actions (precision). Trade-off:
  invalid actions leave no state footprint, so they're currently **ungraded** (see gaps).
- **Deterministic entity ids** (monotonic counters, not `len()`). This is what makes the
  expected state, chaining, and prompts reproducible. Never reuse a freed id.
- **Authoring is offline & the prompt must be self-contained.** The solving agent sees
  *only* the authored `prompt`, never the `open_ended` list — so the repo + question must
  be embedded inline. (A first run stalled because the LLM wrote "see the step below".)
- **Judge endpoint is explicit.** `vf.JudgeConfig` does *not* inherit the eval client;
  it's configured on `ChatTaskConfig.judge`.

## Roadmap / open gaps

1. **Invalid-attempt trace pass.** `p_invalid` actions are currently unrewarded and
   unpenalized (state-diff ignores them; they're well-formed calls; the judge ignores
   them). `adapter.is_error` is kept as the building block — add a fourth pass that checks
   the agent *attempted* each invalid step and got an error, then compose it in.
2. **More ambiguity levels.** Only one moderate level exists. A difficulty ladder
   (explicit → referential → indirect) over the *same* scaffold/verifier is the natural
   next axis — but keep intent uniquely recoverable, or route true goal-ambiguity to a
   judge-only track.
3. **Scale & tune.** Only 3 authored tasks so far (`author.py --num N`). Reward weights
   (0.5/0.2/0.3) are arbitrary; live-gen tasks get a free 0.3 from the vacuous judge.
4. **Housekeeping.** Authored prompts still verbalize invalid steps as "expected to fail"
   (cosmetic). `author.py` imports `openai` (present via verifiers; undeclared in this
   package's pyproject). Consider moving `generate.py`/`verify.py` to a shared location
   once a second environment needs them.

## Context for whoever picks this up

This was built collaboratively as a hands-on way to learn verifiers *and* to develop the
generated-task pattern. The working style has been: **the owner writes/reviews the code;
the assistant guides, and builds only when asked.** Prefer verifiers-native primitives
(`vf.Taskset`/`vf.Task`/`vf.Toolset`/`vf.Judge`/`vf.reward`) over reinventing plumbing.
