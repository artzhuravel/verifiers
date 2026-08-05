# my_env2

Automatically authored multi-step tool-use tasks over a mock chat app.

The idea that shapes everything here: **the sequence comes first and the world is built to
serve it.** Generation runs symbolically — no simulator, no seed, typed placeholders instead of
ids — and only then is a workspace invented in which that sequence is a sensible thing to ask
for. The previous approach was the other way round, and a sequence was whatever a fixed seed
happened to permit.

Two consequences are the point of the whole design:

- **A step can be made to matter.** Because the world is authored to satisfy the sequence, the
  chat a `mark_read` targets can be *made* to have something unread. In the previous pipeline
  8.7% of write links wrote a fact that was already true, which the reward cannot tell from
  doing nothing. Here that is structural for two cases and measured for the rest: replay
  compares the state before and after every step, and drops a task containing a write that
  changed nothing or a read that came back empty.
- **A reference can be made to resolve.** Every entity a prompt talks about is given a
  description proved to match exactly one thing in the finished seed, so the prompt can drop ids
  entirely and the agent has to inspect the environment to work out what is meant.

## Running it

```bash
# offline: what a sequence looks like before anything is authored
uv run python -m my_env2.cli plan --idx 3
uv run python -m my_env2.cli world --idx 3    # a mechanical world for it, replayed

# authoring (needs OPENROUTER_BASE_URL and OPENROUTER_API_KEY)
uv run python -m my_env2.pipeline --num 20 --model openai/gpt-5-nano --out tmp/tasks_v2.jsonl
uv run python -m my_env2.cli task --idx 3 --dataset tmp/tasks_v2.jsonl

# evaluating — `eval.toml` carries the client, the runtimes and the harness
uv run eval @ environments/my_env2/eval.toml
uv run eval @ environments/my_env2/eval.toml --env.taskset.level 1   # the same tasks, spelled out
```

Use `gpt-5-nano` while iterating and `gpt-5-mini` for output meant to be kept. Every call is
cached under `tmp/my_env2_cache/<task id>/`, keyed by the exact prompt, so re-running costs
nothing for the stages that already succeeded.

## The stages

| | | |
|---|---|---|
| 1 | `symbolic.py` | Walk N threads over a shared clock, symbolically. Out: timelines, an entity manifest, the slots authoring must fill, realized shape metrics. |
| 2 | `render.py` | The shared context every later call receives: entity docs and action docs, straight from the spec. |
| 3 | `authoring.py` | Invent the core entities the manifest asks for, as one coherent situation. |
| 4 | `authoring.py` | Give each core entity one description that provably singles it out. |
| 5 | `authoring.py` | Pad the world, one entity at a time, keeping only additions that leave every description unique. |
| 6 | `replay.py` | Bind every placeholder, execute the sequence once against the seed. Out: `expected`, per-step and per-turn diffs, what each read returned. The validity gate. |
| 7 | `authoring.py` | Write the free text. |
| 8 | `prompts.py` | v1: numbered, explicit, ids named. Plus the judge specification. |
| 9 | `prompts.py` | v2: prose, every id replaced by its Stage 4 description. |
| 10 | `prompts.py` | v3: the goal, with no steps left individually identifiable. |

`pipeline.py` runs them in order and refuses what does not fit. Nothing is repaired: a stage
either satisfies its contract or the task is dropped, because patching a draft produces a task
whose prompt describes a world other than the one shipped.

## Why the expensive half runs last

By the time any prose is written, `(seed, expected)` is fixed and every reference has been proved
to resolve. `adapter.signature` excludes text, emoji and chat names by design, so Stage 7 onwards
can decide what the messages actually say without moving a single fact in `expected`. That is
what makes a ten-stage pipeline affordable rather than circular.

## Scoring

Two rewards. `state_diff` (0.6) is F1 between the facts a faithful run adds and the facts this
run added, over `adapter.signature` — path-agnostic, since it compares end states, which matters
because v3 deliberately stops telling the agent what order to work in. `delivery` (0.4) is one
judge call over the Stage 8 specification: information that had to travel from a read into a
message or into the agent's reply, which no state comparison can see.

Between them they cover every step. A write lands in `state_diff` by construction; a read has no
state effect, so it reaches the judge either by being carried into a message or by having to be
reported back. The test suite pins that: no step falls between the two.

## Files

| file | |
|---|---|
| `action_spec.json` | The source of truth. Actions, `produces`/`consumes`, and the reference modes each entity type offers. |
| `spec.py` | Reads it. The one place that knows the spec's field names. |
| `symbolic.py` | Stage 1. |
| `render.py` | Stage 2, and the two renderings of a sequence the later stages read. |
| `authoring.py` | Stages 3, 4, 5, 7. |
| `seed.py` | An authored world becomes a `ChatState`; symbols become ids. Validates, never repairs. |
| `replay.py` | Stage 6. |
| `prompts.py` | Stages 8, 9, 10, and which items need a judge. |
| `adapter.py` | Everything env-specific: executing an action, comparing states, resolving a reference mode. |
| `llm.py` | The authoring model and its cache. |
| `pipeline.py` | The driver, and the `TaskRecord`. |
| `verify.py` | The two rewards. |
| `taskset.py` | Serves persisted records at a chosen prompt level. |
| `cli.py` | Inspection. |
| `state.py`, `servers/` | The chat app itself. |
| `eval.toml` | A runnable eval: client, runtimes, harness and judge in one place. |

`DESIGN.md` is the detailed design: the data model, each stage's contract, the invariants and where
each one holds, and what to change to add an action, a reference mode or a whole environment.
`DECISIONS.md` records every choice the implementation plan left open, and what is deliberately not
built. `samples/` holds twelve authored tasks and the first measurement over them — including the
account of why an apparently clear result from eight of them did not survive four more.

## Tests

```bash
uv run python -m pytest tests/ -q
```

`tests/stub.py` is a world author with no model behind it, which is what lets the deterministic
spine — binding, reference resolution, replay, expected state, judge-item coverage — be exercised
over sixty sequences without an API call.
