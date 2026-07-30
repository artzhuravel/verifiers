# Implementation plan — authoring a chain batch into a prompt

Status: **plan for review**. Nothing below is built yet.

`gen_dependency_chains` produces a symbolic plan: threads of actions on a shared clock,
with dependency edges and self-describing placeholders (`<text>`, `<emoji>`, `<name>`)
where content belongs. `sequential_author.render_steps` renders that plan as an ordered,
numbered list of labelled arguments. This plan covers the step after: turning that list
into a task an agent can be given and a rollout can be scored against.

Scope is **L1 only** — the explicit rung. The ambiguity ladder (L2–L5) rewrites an L1
prompt and is unchanged by this.

---

## 1. Why L1 is not a prose problem

The ladder defines L1 as *"the easy floor: ids, handles and the operations named outright
— nothing to look up."* That licenses a **numbered work order**, which is fortunate,
because the plans this generator produces are frequently not plausible human errands.
`chain_examples.md` §3 is three documentation reads, then a message carrying all three,
then a message carrying only the third, then a message carrying all three again.

Asked to make that read naturally, a model will merge the last two. The plan defines
`expected`, so a merged prompt grades a compliant agent as wrong. **Fidelity is the
property that matters at L1, and it degrades the harder the author works at coherence.**

Coherence is an L2+ concern. The design goal here is therefore to *remove* reasoning from
the authoring model rather than help it reason.

## 2. What is already resolved, and what is left

`render_steps` resolves more than it looks. In particular it classifies every entity
reference against the **seed state** rather than against `depends_on`, so it never prints
an id the agent cannot know in advance — a rollout-created entity always renders as
"the chat produced by step 3". Roughly 2% of unbound references are real dependencies the
generator did not choose to record, and trusting the edge list would make those tasks
unsolvable.

That leaves exactly three things un-resolved:

1. **Content params** — every param that is not an entity reference. The generator
   deliberately refuses to choose these (`adapter._placeholder`).
2. **What a read will return** — needed so that a downstream content requirement is about
   something real.
3. **Register** — prose rather than a labelled argument list.

Everything else is decided.

## 3. Two passes

**Pass 1 — resolve.** Emits content, the results of reads, and the requirements on
delivered output. No prose. This is the artifact the judge and the human verifier consume,
so it must not be produced in the same breath as writing.

**Pass 2 — compose.** Given fully resolved steps, write the prompt. At L1 this is close to
mechanical.

## 4. The one new environment seam

To choose content that is *about* something, the author has to know that `c_005` is the
launch channel. Nothing today can say that generically: `render_steps` can only manage
`"c_005 (a chat that already exists)"`.

Add exactly one method to the `EnvAdapter` protocol:

```python
def describe(self, state: Any, entity_id: str) -> str: ...
```

This is not chain surface. **L2 is defined as "every entity is *described* instead"**, so
the ladder needs it regardless; chains merely surface the need first.

## 5. `returns` replaces `_OPEN_GUIDANCE`

`author._OPEN_GUIDANCE` is a hardcoded per-tool dict explaining that wiki contents returns
prose and that one must never ask it for a licence. The spec already carries this, per
action, in a field the generic core can read:

| action | `returns` |
|---|---|
| `read_wiki_contents` | `documentation text` |
| `read_wiki_structure` | `list of documentation topics` |
| `ask_question` | `free-text answer (nondeterministic)` |

Make those strings precise enough to carry the constraint and the env-specific dict can go,
leaving `author.py` generic. Env knowledge belongs in the env's spec.

Note that OPEN_QUESTIONS §3 records the guidance being present, explicit, and **ignored**
in 3 of 5 tasks. Moving it to `returns` does not fix that on its own — see the validation
gate in §9.

---

## 6. Pass 1 input

Five blocks, each derived from spec + adapter, nothing hardcoded about chat apps:

| block | source |
|---|---|
| **A. Environment** | `_meta.description` + `servers[*].description` |
| **B. World** | for each type in `spec["entities"]`: `objects_of_type(seed, t)` × `describe()` |
| **C. Plan** | `render_steps(...)`, numbered, turn-major, plus thread membership |
| **D. Fill list** | computed — below |
| **E. Rules + schema** | fixed |

Two things are deliberately **withheld**: the `unrelated` flag (a model that knows a step
is a distractor writes throwaway content, which becomes a tell) and the
`chain_steps/*.txt` footer, which labels distractors outright.

### The fill list

Computed deterministically so the model never has to work out what needs filling. For each
step, for each param **not** in `ref_params` — the same distinction `render_steps` already
draws between an entity reference and content:

- **the param is the landing site of a value edge** → a **check**. The author must not
  write content: the value is discovered at rollout time. It writes a requirement, and is
  given the source steps' numbers and their `returns:` strings.
- **otherwise** → **content**. The author writes a literal, guided by `param.description`.

Plus, for each step whose output feeds a value edge, a **finding**: what will this action
return?

Only params whose sampled value **is** a placeholder appear. `create_chat.name` is
`<name>` or `None` by generator draw, and whether a chat is named is structure (it decides
dm vs group). The author picks the string, never the presence.

### Two things the author is never asked for

**Anything derivable from the spec.** `produces.source` already says whether a finding is
internal or external; asking the model to restate it invites it to be wrong.

**A finding the generator already computed.** `produces.source == "internal"` means the
result is known from the sim. Today `Outcome.value` captures only *scalar* internal reads,
so `read_messages` and `list_chats` would be sent to an LLM for a result the simulator just
computed and discarded. Extending `adapter._value` to carry collection results for internal
reads removes both the author and the human verifier from that path. **Only `external`
sources should ever reach the author.**

## 7. Pass 1 output

```
{"content":  [{"step","key","param","value"}],
 "findings": [{"step","key","result","hint"}],
 "checks":   [{"step","key","param","requirement","hint"}],
 "reject":   null | "reason"}
```

### findings vs checks

They sit on opposite ends of a value edge. A **finding** attaches to the *source* — a read
— and says what it turns up. A **check** attaches to the *consumer* — a write — and says
what must be true of the delivered content.

**Only checks are graded.** This is already how the pipeline works: `taskset._transcript`
states that grading targets delivered output alone, *"because the reward measures delivery,
not retrieval"*. A finding is never compared against anything; it is the reference a check
points at. The link needs no field — the consumer's `depends_on` already names its sources
by key.

Three reasons findings are not folded into the checks that use them, measured over 160
batches spanning the config space:

| | |
|---|---|
| sources feeding **2+** consumers | **64.2%** (37.7% two, 16.8% three, 9.8% four or more) |
| consumers fusing **2+** sources | **34.4%** |

- **Duplication.** Fold them in and the same fact is written out by an LLM 2–6 times, in
  slightly different words. One copy being wrong grades a correct agent as wrong.
- **Attribution.** The §3 validator asks *"could an action returning `documentation text`
  produce this claim?"* That is answerable per source and unanswerable against a blob
  fusing three of them — and a third of checks fuse.
- **Verification load.** The human queue is one row per distinct external read. Inlining
  roughly doubles it. Measured external sources per batch: 0 in 75 batches, 1 in 58,
  2 in 23, 3 in 4.

### Why this shape

The schema exists so that checking the output is **set equality against a list you
computed**, not a semantic review of prose:

```
{(kind, key, param) in output} == {(kind, key, param) in fill list}
```

Three arrays rather than a map keyed by step, because the three have different consumers
(pass 2 / the judge / the human queue), different validators, and cardinalities that do not
match steps (0..n content, 0..1 finding, 0..n checks). Keeping them separate also keeps the
stored artifact self-describing: a reader should not need the fill list to know whether a
string is a literal or a predicate.

`step` **and** `key` are both required and cross-checked. `key` is the identity — positions
shift, which is why `gen_dependency_chains` moved off offsets — but the prompt shows the
model numbers, so it has to translate. The failure modes are asymmetric: a wrong key is
almost certainly a nonexistent key and is caught, while a wrong number silently attaches a
check to the wrong step and grades a correct agent against the wrong reference. One
redundant field converts a silent corruption into a hard error.

Content is a bare string and a check needs `requirement` + `hint` because they are
epistemically different: content is a value the author *chooses*, so the check over it is
derivable mechanically; a requirement is a *predicate over something not yet known*.

**There is nowhere in this schema to put prose.** "Pass 1 does not write the prompt" stops
being a rule the model can drift from and becomes structurally impossible.

### Why `reject`

Some plans cannot be authored. Both `add_reaction` steps in `chain_examples.md` §8 target
`m_043`, and `signature` excludes emoji, so the second writes a fact that is already true.
All 13 `mark_read` links in a sampled batch consumed a `create_chat` — marking a chat
created moments earlier and therefore empty. No content makes either verifiable.

Without an exit a model will invent filler (a task that looks fine and grades wrong),
silently drop the step (worse — `expected` still contains it, so a compliant agent is
penalised), or emit unparseable output. `reject` does not grant a capability; it makes an
existing behaviour legible.

The payoff is that it is a **measurement**. `ChainConfig` has five knobs and no feedback
signal today. A typed rejection gives a rate per config point — and it is the cheapest way
for the no-op-link problem (59 of 675 write links leave no state footprint, 8.7%) to
surface as a number rather than as silence.

It is abusable as a lazy escape hatch: require the reason to name a specific step key, and
watch the rate.

## 8. The pass 1 prompt

```
You resolve the CONTENT of an action plan. You do not write prose, and you do
not change the plan. Another step turns your output into a task description.

## ENVIRONMENT
{_meta.description}
{for each server: name — description}

## WORLD  (everything that already exists)
{for each entity type: id — describe(seed, id)}

## PLAN  (already fixed; shown for context)
{render_steps output}
{thread membership}

## RESOLVE EXACTLY THESE
{fill list — one line per item, tagged content / finding / check, carrying
 param.description, or the source's returns: string}

## RULES
1. Resolve only the items listed. Never alter an argument the plan fixed.
2. Only identifiers that appear in WORLD may appear in anything you write.
   Never invent one. Never write an id for something the plan creates — it
   does not exist yet.
3. A finding must be something the action can actually return. Each source
   shows `returns:`. If what you want to claim is not the kind of thing that
   returns, pick a different question.
4. For a check, do not write the content. The value is discovered when the
   task runs. Write what must be TRUE of it.
5. Every check must be decidable from the transcript and the final state alone.
6. Steps that feed each other must be ABOUT THE SAME THING. Content is your
   only freedom, and it is the only thing that makes this read as real work.
7. If a step cannot be given sensible content, reject the whole batch and name
   the step. Do not invent filler.

## OUTPUT
{"content":  [{"step","key","param","value"}],
 "findings": [{"step","key","result","hint"}],
 "checks":   [{"step","key","param","requirement","hint"}],
 "reject":   null | "reason"}
```

Rule 6 carries more weight than it looks. The structure is frozen, so the only lever that
makes `chain_examples.md` §3 read as real work is what the three lookups are *about*: three
unrelated repos summarised into one message is incoherent, three repos in one dependency
stack is a plausible errand. **Coherence is bought in pass 1 by content choice, not in pass
2 by prose.** Pass 2 attempting it is exactly how fidelity is lost.

## 9. The validation gate

Prose is not trusted, per OPEN_QUESTIONS §3. Before any string is read:

- **set equality** against the fill list — nothing missing, nothing invented;
- **`step`/`key` agreement**;
- **id containment** — every `c_*`/`m_*`/`u_*` in any authored string exists in the seed
  (this catches invented ids and created-entity ids in one check);
- **§3 check**, per finding: a cheap second call asking *"could an action documented as
  returning `{returns}` produce `{result}`?"* Reject-and-retry on no, exactly as
  `author._attempt` already does.

`reject` short-circuits: count it against the originating `ChainConfig`, drop the task.

## 10. Resolution — and why it is cheap

`content` is written into `step["args"][param]`, replacing the placeholder.

**This never invalidates `expected`.** `signature` excludes text, emoji and chat names by
construction — OPEN_QUESTIONS §5 verified that `name="retro"`, `"Retro"` and `None` produce
an identical delta. Content is resolved *after* simulation and no re-simulation is needed.
That property is what makes a two-pass design affordable.

## 11. Pass 2

Given resolved steps, compose the prompt. The instructions are mostly prohibitions, and one
dominates:

> The plan may look repetitive, arbitrary, or redundant. **Reproduce it exactly.** Do not
> merge two steps, drop one, reorder them, add one, or explain why any is being asked for.
> If two steps look like duplicates, ask for both.

Two decisions belong to the renderer, not the model:

- **Thread grouping.** Group into "Task A / Task B" sections only when a thread has no
  incoming cross-thread edge. `chain_examples.md` §6 (`p_cross=0`) is three clean sections;
  §3 is fully crossed and must be one flat list. That is a graph property — compute it.
- **Order.** Impose a single total order and say "do them in this order". This
  over-constrains genuinely independent steps but costs nothing: reordering is free under
  canonicalisation (measured 0.793 → 1.000), so the score is unaffected and the last
  ambiguity is removed.

Pass 2 is validated the same way: every step number referenced, instruction count equals
step count, no id outside the seed.

## 12. What the row becomes

```python
prompt: str            # pass 2
seed, expected         # unchanged — authoring never touches them
steps: list[dict]      # real content in args, plus depends_on
checks: list[dict]     # replaces `open_ended`
findings: list[dict]   # referenced by checks, graded never
```

The **human verification queue** is a derived view: findings whose step has
`produces.source == "external"`. One row per read — action, args, claimed result. Internal
findings never appear.

## 13. Scoring

`state_diff` (0.5) and `tool_calls` (0.2) are **untouched**. Content never enters
`signature`, and `tool_call_score` reads only the spec's param schema.

The third reward is rewired. `judge_open_ended` already takes a list of items, renders them
into **one** prompt, and returns the fraction marked true, so the change is confined to
`verify._render_items`: each check becomes one numbered item, with its findings looked up
through `depends_on` and inlined as the reference.

```
3. Requirement: the message must state what each repo is for
   Known: step 1 — nanochat is a minimal full-stack LLM training repo
          step 2 — playwright's docs cover Locators, Assertions, Trace Viewer
   Where to look: the message sent to c_005
```

Findings are never items. They are the reference slot of the checks that consume them.

### This closes OPEN_QUESTIONS §5 as a side effect

Routing message text through checks means the judge now grades a **state change**, not just
an answer, which is exactly the three changes §5 already identified:

- `verify._OPEN_ENDED_PROMPT` tells the judge to use the full rollout *"never as the answer
  itself"* — written for answers; for a state change the state **is** the delivery.
- `taskset._transcript` renders sent messages but not created chats, so a check on
  `create_chat.name` has nothing to grade against.
- A wrong name will cost less than wrong members: membership is deterministic at weight
  0.5, content is a fraction of weight 0.3.

It also closes a gap that predates chaining entirely: message text is verified **nowhere**
today. A prompt asking for "sounds good" is satisfied by an agent sending "ok".

## 14. Open decisions

**The 0.3 weight.** Value edges are 56% of all edges the generator emits (547 vs 425 object
edges) and are visible *only* to the judge; object edges already live in `state_diff` at
0.5. As written, the majority of a chain's dependency structure is graded at 0.3 and the
minority at 0.5. Probably backwards for a chain-centric taskset, but changing it moves every
existing score.

**Rename the reward.** `open_ended` no longer describes what it measures; `content` or
`checks` does. The name appears in eval output.

**Keep the per-item verdicts.** The judge returns a boolean array and `judge_open_ended`
collapses it to a fraction immediately. Since each item is now a specific `(step, param)`,
retaining the array says *which link* failed — a diagnostic that currently has to be
reconstructed by reading transcripts.

**Whether L1 needs an LLM at all.** `render_steps` already emits English from the spec, so
a template over resolved steps would be strictly more faithful than any model. The argument
against is the ladder's premise: a score gap between rungs should be attributable to
ambiguity alone, and generating L1's text by a different mechanism than L2–L5 introduces a
second variable. Recommendation: keep the LLM for register consistency and lean on the
validator — but if an unimpeachable floor matters more than a comparable one, the template
is the better call, and OPEN_QUESTIONS already notes L1 has been an unstable baseline.

## 15. Out of scope

- L2–L5 rewrites — unchanged; they re-anchor to the plan, not to the L1 text.
- The no-op link problem (8.7% of write links leave no state footprint). Deferred
  deliberately; `reject` surfaces it as a rate in the meantime.
- Retirement of `generate.gen_dependency_chain` (superseded by
  `sequential_generate.gen_dependency_chains`, incompatible edge schema, no callers).
