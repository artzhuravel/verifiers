# Automatic task generation — design

Generates imperative tool-use tasks: an ordered sequence of `(action, object)` steps
grouped by timestep, some deliberately invalid, plus the outcome expected of each. The
generator is **environment-agnostic** — it is driven by `action_spec.json` and an
environment **adapter**, and knows nothing about any particular environment.

## Architecture

```
generate(spec, adapter, action_ids, timesteps, max_actions_per_t, p_invalid, idx)
        │  (generic core — reads the spec, samples a valid/invalid action walk)
        ▼
   env adapter  ── initial_state / objects_of_type / invalid_ref / apply
        │  (the only env-specific seam; wraps the env's real tools + state)
        ▼
   returns (seed, timeline)   timeline = [[step, ...], ...]  grouped by timestep
```

The core is a spec-driven sampling loop. Everything env-specific — state, seeding,
tools, value arguments, id minting — lives behind the adapter.

## The action spec

Read from `action_spec.json`. Per action the core needs only declarative facts it
already carries:

- `tool` — the concrete tool name.
- `kind` — `read` | `write`.
- the **object**: the first `entity_exists` precondition's `ref` (which arg names the
  entity) and `entity` (its type), plus whether it is `enforced`. Actions with no
  such precondition have no object (e.g. `list_chats`, `create_chat`).

`enforced` matters because only an enforced object can be made to error — those are the
**invalidatable** actions.

## The adapter seam (env implements exactly this)

- `initial_state(rng) -> state` — the seed. The environment owns seeding.
- `objects_of_type(state, entity_type) -> list[id]` — existing object ids of a type.
- `invalid_ref(entity_type) -> id` — an id guaranteed never to exist.
- `apply(action, object_id, state, rng) -> Outcome` — assembles full args (placing
  `object_id` into the object param and **filling value args like text/emoji/name**),
  runs the env's real tool over `state` (advancing it, or erroring), and returns
  `Outcome(error, entity_id, args)`.

`Outcome.entity_id` is the **id of the created (or affected) entity**. Per the design
decision below, that id is the only content-level thing tracked — names/text/etc. ride
along in `args` (needed to actually call the tool) but are **not** enforced.

## Sampling loop

```
rng   = Random(idx)
sim   = adapter.initial_state(rng)          # mutated during simulation
seed  = adapter.initial_state(Random(idx))  # identical pristine copy for the task
for t in range(timesteps):
    for _ in range(rng.randint(1, max_actions_per_t)):
        if enforceable and rng.random() < p_invalid:
            a = choice(enforceable);  object_id = adapter.invalid_ref(a.type);  kind = "invalid"
        else:
            a = choice(actions whose object type currently has ≥1 id, or has no object)
            object_id = choice(adapter.objects_of_type(sim, a.type)) if a has an object else None
            kind = a.kind
        outcome = adapter.apply(a.id, object_id, sim, rng)   # advances sim; concrete ids
        assert outcome.error == (kind == "invalid")          # generation invariant
        record step {action, tool, kind, object_param, object_id, args, expect_error, entity_id}
```

`sim` advances as we sample, so a later valid action can target an object created
earlier (chaining). Deterministic env ids (the env's counters, surfaced through
`apply`) make the created id knowable at generation time and reproducible by a faithful
agent. RNG is seeded by `idx`, so a task regenerates identically (`--resume`, tracking).

## What is enforced: ids and structure, not content

The only thing tracked for state/id enforcement is the **entity id** an action
creates or affects, plus whether it errored. Value content — the exact `text`, `emoji`,
`name` — is deliberately **not** enforced here; that is left to an LLM judge or custom
hooks added later. This keeps the generator env-agnostic and the reward robust.

## Authoring pipeline (offline, one-time)

Scaffolds are turned into natural-language tasks by an LLM, once, and frozen to a JSONL:

```
generate (deterministic)  →  author.py (LLM)  →  authored_tasks.jsonl  →  taskset (dataset= )  →  eval
  seed/expected/timeline      prompt + golds        + manual human check      GeneratedTask         3 rewards
```

`author.py` renders each scaffold (seed + ordered plan) and asks an LLM to produce ONE
moderate-ambiguity, **self-contained** prompt (natural references, ids not spelled out,
but the intended actions uniquely recoverable) plus, for each open-ended DeepWiki slot,
a `{question, ground_truth, judge_hint}`. The prompt must embed the repo + question
inline — the solving agent sees only the prompt, never the `open_ended` list. The JSONL
is nondeterministic/LLM-costed, so it's the reusable artifact; a human verifies the
golds manually (no `verified` flag in the schema). `ChatTaskset.load()` reads it when
`--env.taskset.dataset <path>` is set, else live-generates scaffolds.

## Reward (three passes, env layer)

Each `GeneratedTask` sums three weighted `@vf.reward`s:

- **`state_diff`** (0.5) — F1 between the **expected** and actual `trace.state`, reduced
  to id/structure facts via `adapter.signature` (message/chat ids, `(msg, reacted_by)`,
  `(msg, read_by)`, `(chat, member)`; content excluded). Scored over the change vs the
  seed: missing expected changes ↓recall, unexpected changes ↓precision (extra creates
  subtract). Extra reads change no state, so they're not penalized.
- **`tool_calls`** (0.2) — `verify.tool_call_score`: fraction of the agent's tool calls
  that are well-formed against the spec's `params`/`required` (missing-required,
  unknown-param, unknown-tool, unparseable → malformed).
- **`open_ended`** (0.3) — `verify.judge_open_ended`: ONE LLM-judge call per task,
  grading the open-ended answers against their golds using the `judge_hint` to locate
  them in the agent's transcript; returns the fraction correct. 1.0 when no open items.
  Its endpoint is configured explicitly (`ChatTaskConfig.judge`) — it does not inherit
  the eval client.

**Known gap:** invalid actions leave no state change and are well-formed calls, so none
of the three passes rewards/penalizes *attempting* them — that needs a future
invalid-attempt trace pass (the `adapter.is_error` helper is kept for it).

## Boundaries

- `generate.py` — the generic core (no env imports). Candidate to move to a shared spot.
- `adapter.py` — `ChatAdapter`: the seam (`initial_state`, `objects_of_type`,
  `invalid_ref`, `apply`, `signature`; `is_error` reserved for the invalid-attempt pass).
- `verify.py` — generic scoring: `score` (state F1), `tool_call_score`, `judge_open_ended`.
- `author.py` — the offline LLM authoring step.
- `taskset.py` — env layer: config, load (live vs dataset), the three rewards.

## Noted extensions

Invalid-attempt trace pass (compose with the three rewards); goal-oriented tasks
(describe an end state, judge-graded); entity deletion (keep counters monotonic).
