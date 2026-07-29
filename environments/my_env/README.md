# my_env — a generated tool-use environment (overview & handoff)

This is a working, end-to-end pipeline for **automatically generating verifiable,
multi-step tool-use tasks** for an LLM agent, and scoring them with a composite verifier.
It doubles as a reusable *pattern* for building generated-task environments: the
generator and scoring core are environment-agnostic (driven by a spec + an adapter), so
only the chat-specific pieces are bespoke.

Read this first. `DESIGN.md`, `HANDOFF.md` and `PRESENTATION.md` now live under `tmp/`.

## What we're trying to achieve

Produce **lots of tasks, cheaply, with trustworthy rewards**, where:

- tasks exercise a realistic tool surface — a mock chat app (fully controlled, local)
  plus a real read-only web tool (**DeepWiki**, GitHub-repo Q&A over MCP);
- each task is a **deterministically sampled action plan** ("scaffold") turned into a
  **natural-language prompt** by an LLM at a chosen rung of an ambiguity ladder (L1
  explicit → L5 noisy), where references get progressively harder to resolve but the
  intended actions stay uniquely recoverable;
- scoring combines **deterministic** signals (did the world end up as intended; were the
  tool calls well-formed) with an **LLM judge** for the open-ended web answers.

The design intentionally separates *plumbing* (deterministic, verified by state/schema)
from *semantics* (content, verified by a judge). Content is never enforced by the
deterministic passes — only entity **ids / structure** are.

## The pipeline

```
generate (deterministic)  →  author.py (LLM, once)  →  authored_tasks_l1..lN  →  human verify  →  eval
   seed + expected +           one NL prompt + golds,     frozen datasets,           check golds     3 rewards
   timeline (action plan)      then N-1 ambiguity rewrites one per ladder rung
```

- **generate** — a random walk over the action spec, using the real tools to advance an
  in-memory state (so created-entity ids are deterministic and validity is exact).
  Returns `(seed, expected_final_state, timeline)`. Open-ended DeepWiki actions are
  emitted as empty **placeholder slots** (no API call at gen time).
- **author.py** — a one-time LLM step: turns each scaffold into a single **self-contained**
  prompt and, for each open slot, a `{question, ground_truth, judge_hint}`. That prompt is
  **L1**; `--levels N` adds one rewrite per further rung (see the ladder below). Each
  rewrite is re-anchored to the original plan, not just handed its predecessor, so chained
  rewrites don't accumulate drift. A task that fails at any rung is dropped from every
  file, keeping the levels comparable.
- **human verify** — a person checks the LLM-authored gold answers are actually true
  (tracked manually; there is deliberately **no `verified` flag** in the schema).
- **eval** — the taskset loads the dataset and scores each task with three rewards.

## The ambiguity ladder

Each rung is a rewrite of the same task adding one class of indirection. The **plan never
changes** — for a given task the seed, expected state, steps and golds are byte-identical
across every rung, so a score gap is attributable to the wording alone.

| rung | adds | e.g. how one chat gets referred to |
|---|---|---|
| **L1** explicit | the easy floor: ids, handles and the operations named outright — nothing to look up | "the DM with Alex Chen (@alex.chen)" |
| **L2** descriptive | scaffolding stripped — no numbering, tool names, ids or handles, and no chat titles; every entity is *described* instead | "the DM with the colleague who asked 'Do you have a read on the Q3 date?'" |
| **L3** relational | descriptions become **relationships and ordering** ("the oldest unread…", "whoever pushed back on…"), which cannot be resolved from the prompt — the agent must inspect the app | "the DM where the other person *most recently* asked about the Q3 date" |
| **L4** conditional | some requests move behind a **condition evaluated against live state**, with a plausible branch that must *not* fire | "*if* that message has no reactions yet, …; otherwise skip" |
| **L5** noisy | 2–5 realistic typos in the prose only — never inside quoted strings, repo names or identifiers, which the golds are keyed to | (wording unchanged; "Pleasse", "Lookk up") |

Ambiguity is **referential, not semantic**: the intended action set must stay uniquely
recoverable at every rung. A rewrite that makes the task genuinely underdetermined is a
defect, not a harder task — and nothing currently detects that (see `HANDOFF.md` §8.1).

`samples_v3/ladder_example.md` shows one real plan rendered at all five rungs.

## Scoring (three weighted rewards on `GeneratedTask`)

| reward | weight | what it measures | how |
|---|---|---|---|
| `state_diff` | 0.5 | did the chat end up as intended | F1 of expected vs actual `trace.state` as id/structure facts (`adapter.signature`); missing → ↓recall, extra → ↓precision. Content excluded. |
| `tool_calls` | 0.2 | were the calls well-formed | fraction of calls valid against the spec's `params`/`required` (`verify.tool_call_score`) |
| `open_ended` | 0.3 | were the DeepWiki answers correct | ONE LLM-judge call/task grading answers vs golds via `judge_hint` (`verify.judge_open_ended`); 1.0 if no open items |

Both deterministic passes were verified to *discriminate* (faithful → 1.0; missing/extra/
malformed → lower), and the judge too (all-right 1.0, one-wrong 0.5, all-wrong 0.0). A
competent agent on well-authored tasks earns ~1.0 across all three.

### How entities are identified when two states are compared

Entities that came from the seed keep their real ids — those mean the same thing in every
trajectory. Entities the *rollout created* are keyed by **what they are** (a chat by its
member set, a message by its chat + sender + parent) plus an occurrence index, never by
their minted id. A minted id is an artifact of a counter: an agent that creates one extra
entity shifts every later id, and id-based comparison would then score its correct work
against structurally unrelated entities. Concretely, `('chat','c_007')` plus its
`('member','c_007',…)` facts collapses to a single `('new_chat', (members…), 1)`.

| same final state, scored | id-keyed | canonical |
|---|---|---|
| faithful | 1.000 | 1.000 |
| two creates **reordered** | 0.793 | **1.000** |
| one **extra** create | 0.693 | **0.916** |

Reordering is free (it is the same work), and an extra create costs one entity's worth
instead of cascading. The *content* of a created message — its text — is deliberately not
part of its identity; that is the judge's job.

## Current state

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
| `state.py` | schema: `User`/`Message`/`Chat` + `ChatState` + deterministic id counters |
| `world.py` | the seeded workspace — 24 users, 6 chats, 40 threaded messages, built per task |
| `servers/tool.py` | `ChatToolset` — local chat tools on `self.state` |
| `servers/web.py` | `DeepWikiToolset` — remote read-only GitHub Q&A |
| `action_spec.json` | machine-readable action contract (generator + tool-call verifier read it) |
| `generate.py` | **env-agnostic** scaffold generator (spec + adapter → seed/expected/timeline) |
| `adapter.py` | `ChatAdapter` — the env seam (`initial_state`/`objects_of_type`/`invalid_ref`/`apply`/`signature`) |
| `verify.py` | the three scoring passes (generic; env specifics come from the adapter/spec) |
| `author.py` | one-time LLM authoring step + the ambiguity ladder → `authored_tasks_l*.jsonl` |
| `taskset.py` | env layer: config, `load()` (live vs dataset), the three `@vf.reward`s |
| `samples_v3/authored_tasks_l1..l5.jsonl` | the frozen authored datasets — one per ambiguity rung, same tasks in each |
| `samples_v3/ladder_example.md` | worked example: one plan rendered at every rung — the best single explainer |
| `samples_v3/sample_output.json` | inspection artifact: raw `generate` output (seed/expected/timeline) |
| `samples_v3/rescore/` | latest eval (post-signature-fix): `eval_results.md` + `transcripts/l*.md` |
| `my_env/cli.py` | `plan` / `prompts` / `result` inspection commands (driven by `./tasks`) |

Superseded artifacts (the pre-ladder dataset, `samples_v2/`, the old-world
`sample_output.json`, and the unused `legacy_tasksets.py`) were moved to `tmp/` at the
repo root — kept for reference, excluded from git via `.git/info/exclude`.

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
uv run --with-editable environments/my_env python -m my_env.author \
  --num 12 --levels 5 --out-dir environments/my_env/samples_v3
uv run --with-editable environments/my_env eval my_env \
  --env.taskset.dataset environments/my_env/samples_v3/authored_tasks_l3.jsonl \
  --env.agent.harness.id null -m openai/gpt-5-nano \
  --client.base-url "$OPENROUTER_BASE_URL" --client.api-key-var OPENROUTER_API_KEY --no-push
```

Taskset and harness options live **under `--env.`** (`--env.taskset.*`,
`--env.agent.harness.*`); `--client.*` and `-m` sit at the top level. Dotted names accept
hyphens or underscores. `--uuid <name>` names the output-directory leaf, and `-o <dir>`
writes the run somewhere specific — both make collecting results scriptable.

`--levels N` controls how far up the ladder to author (1–5). Swap `_l3` for `_l1`…`_l5` at
eval time to move along it. Every level file holds the
same tasks — identical seed, expected state, steps and golds — so a score difference
between two of them is attributable to the phrasing, not to authoring noise.

Quick, no-authoring iteration on scaffolds (open-ended items ungraded, prompts are a
stopgap): the same command **without** `--env.taskset.dataset`.

Requires a POSIX host — `verifiers.v1` imports `fcntl`, so it does not run on native
Windows.

Config knobs — taskset: `dataset`, `num_generated`, `timesteps`, `max_actions_per_t`,
`p_invalid`, `p_open`; per-task: `tools`, `web` (DeepWiki url), `judge` (judge endpoint/model).

## Key decisions

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
