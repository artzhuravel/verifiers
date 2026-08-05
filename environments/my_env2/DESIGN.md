# Design

How the pipeline works, in enough detail to change it. `README.md` is the overview and how to run
it; `DECISIONS.md` is why each contested choice went the way it did. This file is the mechanism.

## 1. The inversion

The previous pipeline sampled a sequence of actions **against a fixed world**. Every question it
could not answer followed from that: whether a `mark_read` had anything to mark, whether a read
returned anything worth carrying, whether the chat a prompt described was the only one matching that
description. All of them are properties of the world, and the world was already decided.

This pipeline runs the other way. A sequence is generated **symbolically** — no simulator, no seed,
typed placeholders where ids would be — and the world is then invented to satisfy it. The same
questions become constructive rather than diagnostic: the chat *is given* something unread, the read
*is given* history, the description *is chosen* to match one thing.

Everything below is downstream of that one decision. The cost of it is that `expected` is no longer
free — the old walker's simulator *was* the end state — so there is an explicit binding-and-replay
stage, and that stage becomes the pipeline's validity gate.

## 2. The pipeline at a glance

| # | module | in | out | can drop the task |
|---|---|---|---|---|
| 1 | `symbolic.py` | spec, rng, thread configs | `Sequence`: steps, manifest, slots, shape | no — it cannot fail |
| 2 | `render.py` | spec, sequence | shared context string | no |
| 3 | `authoring.py` | context, plan, manifest | `WorldDraft` | yes — unbuildable draft |
| — | `seed.py` | draft | `ChatState` + symbol→id binding | yes — same |
| 4 | `authoring.py` | world, modes | `symbol → reference` | yes — no mode fits |
| 5 | `authoring.py` | draft, references | padded `WorldDraft` | no — falls back to core |
| 6 | `replay.py` | sequence, seed, binding | `Replay`: expected, observations, diffs | yes — error, no-op, empty read |
| 7 | `authoring.py` | world, plan | `placeholder → text` | yes — a placeholder unfilled |
| 8 | `prompts.py` | plan, judge targets | v1 + judge spec | yes — no prompt, no expected answer |
| 9 | `prompts.py` | v1, references | v2 | yes — no prompt |
| 10 | `prompts.py` | v2, references | v3 | yes — no prompt |

`pipeline.build_task` runs them in that order and returns a `TaskRecord`, or raises. `pipeline.main`
catches everything per task, records the reason, and carries on — the output file is written after
the loop, so an exception escaping would discard every task already built.

Stages 3, 4, 5, 7, 8, 9 and 10 are model calls: seven per task, plus one for each correction round
that fires. Over the last twelve tasks that came to 90 calls, so roughly one correction every two
tasks.

## 3. Data model

### `Sequence` (`symbolic.py`)

```
task_id     str
timelines   [thread][turn] -> [Step]     aligned on a shared clock, equal lengths
steps       [Step]                        the same steps flattened turn-major
manifest    [ManifestEntry]
slots       [Slot]
shape       dict
```

`steps` is turn-major and that is **already a valid topological order**: a source always sits in a
strictly earlier turn than anything consuming it, so nothing needs sorting and every "step N"
in a prompt is just an index into this list.

### `Step`

```
key                 "c0a1"   thread 0, its second emission
chain, turn         where it sits on the clock
action, tool, kind  from the spec
external            no state effect, nondeterministic result (DeepWiki)
refs      {param: symbol | [symbol]}   entity arguments
content   {param: placeholder}         free text, filled at Stage 7
carries   {param: [source keys]}       text that must contain what those steps returned
produces_entity   symbol | None        an entity this step creates ($new_chat_0)
produces_value    symbol | None        information this step returns ($info_0)
depends_on  [{source, via, param, symbol}]
unrelated   bool                       a distractor, but still required work
```

The three param dicts are kept apart rather than merged into one `args` because three different
things fill them at three different times: `refs` by binding at replay, `content` by the authoring
pass, `carries` by the agent at rollout time. Merging them would force every consumer to re-derive
which is which.

### `ManifestEntry`

```
symbol, entity_type
origin        "seed"    must exist before the rollout — Stage 3 invents it
              "rollout" the agent creates it — nothing to invent
created_by    step key, for a rollout entity
roles         [{step, action, param, kind, description}]
requirements  [str]     from the spec's meaningful_when
```

`origin` is the load-bearing field. Stage 3 binds seed symbols and only those; Stage 4 describes
seed entities and only those; Stage 6 binds rollout symbols as the steps that create them run.
Rollout symbols are named `$new_chat_0` so that a model reading the plan cannot confuse the two.

### `Slot`

`{key, param, kind, description, sources}` where `kind` is `content` (free text Stage 7 writes) or
`carry` (text a value edge already determined, which becomes a judge item).

### `shape`

Fifteen measured values: `threads`, `turns`, `steps`, `links_per_thread`, `longest_chain`,
`longest_chain_per_thread`, `cross_thread_edges`, `object_edges`, `value_edges`, `fan_in`,
`fan_out`, `external_steps`, `write_steps`, `distractors`, `actions`. All read off the emitted
steps, never off a config: a thread truncates silently when it runs out of moves, so configured
depth is an aspiration. `links_per_thread` and `longest_chain` are separate on purpose — a thread's
links can all hang off one foreign source, which is a fan-out two deep however many links it has.

### `WorldDraft` (`seed.py`)

The authored world before it becomes a state. Entities refer to each other by **local keys the
model invented** (`u1`, `c2`, `m3`), never by real ids, which do not exist yet. `symbol` links an
entry to a manifest placeholder. `order` places a message on one shared clock across all chats.

### `Replay` (`replay.py`)

```
expected      ChatState after a faithful run
binding       every symbol -> real id, seed and rollout alike
observed      step key -> what that read returned
args          step key -> the concrete args replay used
step_deltas   step key -> the facts that step added
turn_diffs    per turn: the facts that turn added
no_ops        write steps that changed nothing
barren        reads that came back empty
```

### `TaskRecord` (`pipeline.py`)

One row per task, carrying all of the above plus `prompts` (three), `judge`, `references`,
`content`, `expected_facts` and `warnings`. Nothing is thrown away: the record is meant to be enough
to debug a failed rollout without re-running any stage.

## 4. Stage 1 — the symbolic walker

N threads advance over a shared clock. Each turn, each active thread either skips (`p_skip`) or
emits one step; a step is a **root** (depends on nothing, mints what it needs) or a **link**
(consumes something produced in a strictly earlier turn). `p_cross` decides per action whether a
thread may draw on another thread's output. A thread stops when it hits `max_depth` or when nothing
in the pool can be consumed — it terminates, it never raises, so no feasibility look-ahead is needed.

Removing the simulator removed the only other reason a step could stall, and also removed the need
for the old `frozen` snapshot: the pool's strictly-earlier rule is now the whole story, because
minting creates no dependency at all.

Three things the walker refuses to emit, each of which was a measured waste in the previous
pipeline (see `DECISIONS.md` for the numbers):

- an action with `meaningful_when` applied twice to the same entity;
- an action with `requires_history` bound to a rollout-created entity;
- a second occurrence of a parameterless action, which is the same call again.

Unbound entity params reuse an already-minted seed symbol with probability `p_reuse` (default 0.5).
That is what lets two steps share a subject, and therefore what lets a prompt say "that chat".

## 5. Three kinds of edge, two components of reward

This is the mapping the whole design turns on.

| edge | what travels | who can see it |
|---|---|---|
| **object** | an entity id | `state_diff` — the effect is in the state |
| **value** | what a read returned | the judge only — the state shows a message exists, never what is in it |
| **none** (content) | text the author invented | nobody, deliberately |

A step gets at most one edge-bearing param; the rest of its entity params are minted from the seed.
Object edges become `refs`, value edges become `carries`.

`judge_items` derives what needs judging, in code, from that structure alone:

- **carry** — a value edge, so the downstream message must contain what the source returned;
- **report** — an info producer nothing carries, whose answer has nowhere to land but the reply.

Between them these cover every read. Writes are covered by `state_diff` by construction. No step
falls between the two, and `tests/test_pipeline_offline.py` pins that.

**Where** each answer must be delivered is derived, not asked for. An author free to choose a
destination invents a message the plan does not contain, and `state_diff` then penalises the agent
for obeying the prompt. Only the expected answer and the hint are authored.

Authored free text is not judged at all: the author invented it, so checking the agent reproduced it
word for word measures obedience to phrasing — and v3 removes the phrasing.

## 6. Stages 3–5 — building the world

**Stage 3** is shown the shared context, the plan with placeholders, and the manifest with its
`REQUIRED:` lines. It returns a whole small workspace. `seed.build` turns it into a `ChatState`:
users get `u_<handle-slug>` ids, chats `c_001…` in draft order, messages `m_001…` in **clock**
order, and every `symbol` becomes an entry in the binding.

`build` validates and never repairs. Undeclared senders, undeclared reactors, non-member senders or
reactors, replies across chats, replies before their parent, duplicate local keys, colliding
handles, unbound placeholders, placeholders of the wrong type, placeholders nobody asked for — all
`DraftError`. Three things it enforces rather than asks for: the actor is a member of every chat,
the actor never reacts in the seed, and the actor's handle is reserved.

**Stage 4** gives each seed entity one way of being described. The model picks the mode; the adapter
derives params and proves `resolve(state, mode, params) == [entity]`. Modes are tried in the model's
order first, then in declared order, which runs most-indirect-first. Every declared mode is tried
before the stage gives up, and giving up raises rather than shipping: Stage 9 strips ids out
entirely, so an entity without a working reference yields not a harder task but an unanswerable one.
In twelve tasks it has not yet given up.

**Stage 5** pads the world. Filler is folded in **one entity at a time**, each kept only if every
reference still resolves to exactly its own entity, in clock order so threaded filler survives. It
is shown the world in the *draft's* vocabulary, since that is the only vocabulary it can write in.
Rejected items are recorded in `warnings`, never silently dropped. Stage 5 cannot fail the task: a
world without padding is weaker, not broken.

## 7. Stage 6 — binding and replay, and why it is the gate

Every earlier stage is a proposal: the sequence proposes a shape, the authoring stages propose a
world. Stage 6 is the first point at which the two are made to meet.

It walks `sequence.steps` in order against a deep copy of the seed. Entity params are bound from the
binding; content and carry params are written as the placeholder itself (`$text_0`,
`$carried_c0a1_text`) — deliberately conspicuous, so one leaking into a shipped message body would
be unmistakable. External steps are skipped entirely. After each step it takes a signature and
records the delta.

Three ways a task dies here, and the second two are the interesting ones:

1. **an action errors** — the proposals do not fit;
2. **a write changed nothing the reward can see** — the world was authored wrong; every `REQUIRED:`
   line exists to prevent exactly this;
3. **a read came back empty** — same failure on the read side, and easier to miss, because nothing
   errors and the state diff has nothing to say about a read either way. The judge item built from
   it would demand information that does not exist.

Both (2) and (3) are **measured**, not predicted. A predicate over args would have to reimplement
each tool's effect logic in a second place and the two would drift; comparing signatures before and
after cannot.

Free text stays unresolved here, and that is what makes the whole ordering work: `signature`
excludes text, emoji and chat names, so Stages 7 onward decide what the messages actually say
without moving a single fact in `expected`.

## 8. Stages 7–10 — the prose

Stage 7 fills the content placeholders against the now-concrete world and the observed read results.
Stages 8–10 write the same task three ways over one `(seed, expected)` pair:

- **v1** numbered, ids named — the floor;
- **v2** prose, every id replaced by its Stage 4 description;
- **v3** the goal, with no step individually identifiable.

v2 and v3 are given a **forbidden list**: every seed id, every action and tool name, and — for each
entity the prompt is supposed to *describe* — whatever would identify it outright, minus whatever
the assigned reference itself says. Afterwards `_complaints` checks the same list on word boundaries
and flags surviving enumeration. Findings are recorded as warnings, not enforced; an automated
ambiguity check is deferred.

## 9. The environment seam

The pipeline is env-agnostic. Stage 1 reads only `produces`/`consumes`/`preconditions`; the
authoring stages read only the spec's English — an action's `description`, a param's `description`,
an entity type's `description`, an action's `returns`. Four kinds of thing cannot be expressed that
way — executing an action, naming what it produced, comparing two states, and resolving a
description — and they are the whole of `adapter.py`:

| method | used by |
|---|---|
| `execute(action, args, state)` | replay |
| `is_error`, `created`, `observed` | replay — did it fail, what did it make, what did it return |
| `objects_of_type` | the contract tests, which is the only place that has to enumerate |
| `signature(state, seed)` | the deterministic reward, and replay's no-op gate |
| `resolve(state, mode, params)` | Stage 4 uniqueness, Stage 5 preservation |
| `mode_params(state, mode, entity)` | Stage 4 — derive params that provably resolve |
| `describe`, `giveaways` | authoring prompts, and the forbidden list |

Porting to another environment means: a new `action_spec.json` with `entities[*].reference_modes`,
a new adapter implementing the table above, and a new state/toolset. Nothing in `symbolic.py`,
`render.py`, `authoring.py`, `prompts.py` or `pipeline.py` should need to change.

`seed.py` is the exception and is honest about it: turning an authored draft into a state is
environment-specific, and it lives in its own module for that reason.

## 10. Invariants, and where each one holds

| invariant | held by |
|---|---|
| No concrete id escapes Stage 1 | construction — the only two minting sites |
| Every referenced symbol is in the manifest, with the right origin | construction; pinned by test |
| Edges point strictly backwards | the pool's strictly-earlier rule; pinned by test |
| Every seed placeholder is instantiated exactly once, at the right type | `seed._check_binding` |
| The actor is in every chat, and never reacts | `seed.build` |
| No two handles collide | `seed.build`, by rejection |
| Every core entity has a reference that provably resolves | Stage 4, by exhaustion over modes |
| Every reference still resolves after padding | Stage 5 per addition, re-checked in `build_task` |
| Every symbol is bound after replay | `replay`, explicit check |
| No write is a no-op, no read is empty | `replay`, measured |
| Every step reaches at least one reward component | `judge_items` + `state_diff`; pinned by test |

## 11. Cost, caching, retries

Seven model calls per task, plus corrections. The cache is keyed by **task id, stage, model and
a hash of the exact prompt** — not by task id alone, because editing a stage's prompt and silently
getting the old answer back is far worse than re-paying for an unchanged one. Every call is written
out in full, prompt included, so a run can be audited without re-running it. In practice a re-run
after a prompt edit costs only the stages downstream of the edit: the last 12-task run made 36 live
calls and served 54 from cache.

The retry policy is one corrective round: a reply that parses but fails its stage's contract is
handed back its own rejection message, and a second failure drops the task. Nothing is ever patched
by us. A patched world is one the prompt no longer describes, and no amount of scoring catches that.

## 12. Changing things

**Adding an action** — add it to `action_spec.json` with `produces`/`consumes`, implement the tool,
and teach the adapter `created`/`observed` if it makes or returns anything. The walker picks it up
with no code change. Add `meaningful_when` if a second application would write a fact already true,
and `requires_history` if it needs an entity that pre-dates the rollout.

**Adding a reference mode** — declare it under `entities[<type>].reference_modes` with `predicate`,
`phrase` and `readable_via`, then implement `_mode_<id>` and a branch of `_derive` in the adapter.
Declared order is the fallback order, so put it where its indirection belongs.
`tests/test_pipeline_offline.py::test_declared_modes_and_implemented_modes_agree` will catch a
declaration with no implementation.

**Changing the thread mix** — `pipeline.DEFAULT_CONFIGS`. The third, one-link thread is not
decorative: a single-link thread may open with a sink, and that is the only route by which an action
needing pre-existing history reaches a task as real work rather than as a distractor.

**Tests** — `tests/stub.py` is a world author with no model behind it, which is what lets the
deterministic spine be exercised over sixty sequences without an API call. Any change to Stages 1,
4, 5 or 6 should be checkable there before a single token is spent.
