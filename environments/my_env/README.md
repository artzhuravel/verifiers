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
  **natural-language prompt** by an LLM at a chosen rung of an ambiguity ladder (L1
  explicit → L3 relational), where references get progressively harder to resolve but the
  intended actions stay uniquely recoverable);
- scoring combines **deterministic** signals (did the world end up as intended; were the
  tool calls well-formed) with an **LLM judge** for the open-ended web answers.

The design intentionally separates *plumbing* (deterministic, verified by state/schema)
from *semantics* (content, verified by a judge). Content is never enforced by the
deterministic passes — only entity **ids / structure** are.

## The pipeline

```
generate (deterministic)  →  author.py (LLM, once)  →  authored_tasks_l1..l3  →  human verify  →  eval
   seed + expected +           one NL prompt + golds,     frozen datasets,           check golds     3 rewards
   timeline (action plan)      then 2 ambiguity rewrites  one per ladder rung
```

- **generate** — a random walk over the action spec, using the real tools to advance an
  in-memory state (so created-entity ids are deterministic and validity is exact).
  Returns `(seed, expected_final_state, timeline)`. Open-ended DeepWiki actions are
  emitted as empty **placeholder slots** (no API call at gen time).
- **author.py** — a one-time LLM step: turns each scaffold into a single **self-contained**
  prompt and, for each open slot, a `{question, ground_truth, judge_hint}`. That prompt is
  **L1** (explicit — the easy floor). Two further rewrites layer on ambiguity:
  **L2** descriptive/de-scaffolded (names and chat titles forbidden) → **L3**
  relational/temporal. Each rewrite is re-anchored to the original plan, not just handed its
  predecessor, so chained rewrites don't accumulate drift. A task that fails at any rung is
  dropped from every file, keeping the levels comparable.
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

- Chat app: `state.py` (schema + deterministic id counters), `world.py` (the seeded
  workspace), `servers/tool.py` (`ChatToolset`: 3 read + 5 write tools), `servers/web.py`
  (`DeepWikiToolset`, remote).
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
| `world.py` | the seeded workspace — 24 users, 6 chats, 40 threaded messages, built per task |
| `servers/tool.py` | `ChatToolset` — local chat tools on `self.state` |
| `servers/web.py` | `DeepWikiToolset` — remote read-only GitHub Q&A |
| `action_spec.json` | machine-readable action contract (generator + tool-call verifier read it) |
| `generate.py` | **env-agnostic** scaffold generator (spec + adapter → seed/expected/timeline) |
| `adapter.py` | `ChatAdapter` — the env seam (`initial_state`/`objects_of_type`/`invalid_ref`/`apply`/`signature`) |
| `verify.py` | the three scoring passes (generic; env specifics come from the adapter/spec) |
| `author.py` | one-time LLM authoring step + the ambiguity ladder → `authored_tasks_l*.jsonl` |
| `taskset.py` | env layer: config, `load()` (live vs dataset), the three `@vf.reward`s |
| `authored_tasks_l1..l3.jsonl` | the frozen authored datasets — one per ambiguity rung, same tasks in each |
| `sample_output.json` | inspection artifact: raw `generate` output (seed/expected/timeline) |
| `legacy_tasksets.py` | hand-written demo tasks (reference; **not loaded**) |
| `DESIGN.md` | generator/adapter/verifier internals |

## How to run

Set OpenRouter creds (agent + judge both use them):

```bash
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
export OPENROUTER_API_KEY=...
```

`my_env` is deliberately not a workspace member (the root `pyproject.toml` takes no new
deps), so layer it into each command with `--with-editable` — a bare `uv run` re-syncs
the project env and drops it.

Author a batch, then eval one rung of the ladder:

```bash
uv run --with-editable environments/my_env python -m my_env.author --num 12 --levels 3
uv run --with-editable environments/my_env eval my_env \
  --taskset.dataset environments/my_env/my_env/authored_tasks_l3.jsonl \
  --harness.id null -m openai/gpt-5-nano \
  --client.base-url "$OPENROUTER_BASE_URL" --client.api-key-var OPENROUTER_API_KEY --no-push
```

Swap `_l3` for `_l1`…`_l3` to move along the ambiguity ladder. Every level file holds the
same tasks — identical seed, expected state, steps and golds — so a score difference
between two of them is attributable to the phrasing, not to authoring noise.

Quick, no-authoring iteration on scaffolds (open-ended items ungraded, prompts are a
stopgap): the same command **without** `--taskset.dataset`.

Requires a POSIX host — `verifiers.v1` imports `fcntl`, so it does not run on native
Windows.

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
2. **No solvability check on the ladder.** Nothing verifies that an L2/L3 rewrite kept the
   intent uniquely recoverable, so a broken prompt and a genuinely hard one produce the
   same reward. The intended fix is a solve-check: hand a model only the seed state and the
   prompt, have it reconstruct the action plan, and compare `(tool, object_id)` pairs
   against the ground truth we already hold. Until then, read a sample per rung.
3. **Tune.** Reward weights (0.5/0.2/0.3) are arbitrary; live-gen tasks get a free 0.3 from
   the vacuous judge, as do dataset tasks with no open-ended items. The judge now reads the
   whole rollout, which made it markedly more expensive than the agent it grades — worth
   revisiting if batches grow.
4. **Housekeeping.** Authored prompts still verbalize invalid steps as "expected to fail"
   (cosmetic). `author.py` imports `openai` (present via verifiers; undeclared in this
   package's pyproject). Consider moving `generate.py`/`verify.py` to a shared location
   once a second environment needs them.

## Context for whoever picks this up

This was built collaboratively as a hands-on way to learn verifiers *and* to develop the
generated-task pattern. The working style has been: **the owner writes/reviews the code;
the assistant guides, and builds only when asked.** Prefer verifiers-native primitives
(`vf.Taskset`/`vf.Task`/`vf.Toolset`/`vf.Judge`/`vf.reward`) over reinventing plumbing.
