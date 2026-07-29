# Implementation plan — `gen_dependency_chain`

Status: **plan for review**. Nothing below is built yet.

Goal: one function that produces a chain of *N* actions where each link consumes the
output of the previous one, advances the simulation so the caller can derive the expected
state exactly as it does today, and reports the dependency edges so the authoring step
knows where content obligations belong.

Placement of the chain inside a task (contiguous vs interleaved, turns) is **out of scope
here** — this function only builds a valid chain and hands it back.

---

## 1. Why the spec must change first

The sampler currently knows which *objects* an action needs (from `preconditions`) but not
what an action *yields*. Chaining needs the yield side, and it needs to distinguish two
things that behave completely differently downstream:

- an **entity** added to the state (a chat, a message) — consumed through an *object*
  slot, verified deterministically by `state_diff`;
- an **outcome** the model reads but that does not change the replica (a user record, a
  chat's messages, a DeepWiki answer) — consumed through a *value* slot, verified by an
  authored content obligation.

Outcomes split again by who can know the answer: `internal` (computable from the seed at
generation time) vs `external` (only the authoring LLM can supply a gold, and a human
verifies it).

### Proposed additions to `action_spec.json`

Two new keys per action. Everything already there stays untouched.

```jsonc
"produces": { "kind": "entity", "type": "message" }          // state entity
"produces": { "kind": "info", "type": "text",
               "source": "internal",        // internal = gold computable from the seed
               "shape":  "scalar" }         // scalar = one nameable value; collection = a list
"produces": null                                              // sink

"consumes": [
  { "param": "chat_id", "slot": "object", "type": "chat" },   // takes an entity ref
  { "param": "text",    "slot": "value",  "type": "text" }    // takes read content
]
```

Filled in for all eleven actions:

| action | produces | consumes |
|---|---|---|
| `list_chats` | `info/text` internal, **collection** | — |
| `read_messages` | `info/text` internal, **collection** | `chat_id` object:chat |
| `get_user` | `info/text` internal, **scalar** | `user_id` object:user |
| `send_message` | `entity/message` | `chat_id` object:chat · `text` value:text |
| `reply_to` | `entity/message` | `message_id` object:message · `text` value:text |
| `add_reaction` | **null (sink)** | `message_id` object:message |
| `mark_read` | **null (sink)** | `chat_id` object:chat |
| `create_chat` | `entity/chat` | `member_ids` object:user[] · `name` value:text |
| `ask_question` | `info/text` external, scalar | — |
| `read_wiki_contents` | `info/text` external, collection | — |
| `read_wiki_structure` | `info/text` external, collection | — |

Notes that fall out of this table:

- Only **chat** and **message** are ever produced as entities; no action creates a user.
  So `create_chat.member_ids` (the one list-valued object slot) can never be a chain
  target, and v1 needs no list-binding logic.
- `list_chats` consumes nothing, so it can only ever be the **first** link.
- DeepWiki actions consume nothing in v1. (`repoName` is a plausible value slot — "read a
  repo name out of a chat, then ask about it" — but `world.py` contains no repo names, so
  it would never fire. Listed as a follow-up, not built.)

## 2. Two kinds of edge, bound differently

This is the crux, and it follows from the earlier decision that **content is the authoring
layer's business, not the generator's**:

| edge | what the generator does | verified by |
|---|---|---|
| **object** (entity) | *binds* the consumer's param to the produced id — `send_message(chat_id=<the chat just created>)` | `state_diff`, already works |
| **value** (info) | *marks* the edge only. The arg keeps its filler (`rng.choice(_TEXTS)`); the generator does **not** invent content | an authored content obligation — **the judge**; see §9 |

So a value edge is a **declaration that this step's content depends on step k**, which the
authoring LLM then turns into prose and a `judge_hint`. The generator never pins the text.

For `internal` producers the adapter *can* compute the underlying value (e.g. `get_user`
→ handle `praman`); it is returned as `Outcome.value` so the author can be shown it and a
claimed gold can be validated against the seed. For `external` producers the value is
`None` — deferred to authoring.

## 3. Guaranteeing the requested length

Enforced structurally rather than by retrying: **sinks are filtered out of the candidate
set for every link except the last.** Verified that this is always satisfiable —

| last output | non-sink consumers available |
|---|---|
| chat (entity) | `read_messages`, `send_message` |
| message (entity) | `reply_to` |
| info (text) | `send_message`, `reply_to`, `create_chat` |

Every output type has at least one non-sink consumer, so a chain of any length can always
be continued, and `add_reaction` / `mark_read` are reserved for the final link. The
function therefore returns **exactly** the requested length or raises — no best-effort
truncation.

`reply_to` consuming a message and producing a message is what makes arbitrary depth work.
Guard: a run of many consecutive `reply_to`s is legal but dull, so bias selection away
from immediately repeating the previous action unless it is the only option.

## 4. The function

Lives in `generate.py` (the env-agnostic core) — it is driven entirely by the spec plus the
adapter, exactly like `generate`.

```python
def gen_dependency_chain(spec, adapter, sim, rng, length, *, allow_external=True) -> list[dict]:
    """Build `length` actions where each consumes the previous one's output.

    Advances `sim` in place, so the caller derives the expected state exactly as it does
    now (one simulation, one final state). Returns the ordered steps; the caller splices
    them into its timeline as-is — `depends_on` offsets are relative and survive splicing
    unchanged, provided the caller keeps the links in order.
    """
```

Algorithm:

1. Index the spec once into `producers` and `consumers_by_type`.
2. **First link** — sample an action with `produces != null` whose own preconditions are
   satisfiable against `sim` (and respecting `allow_external`). Apply it via
   `adapter.apply`; record the outcome.
3. **Each subsequent link** —
   a. candidates = actions consuming the previous output's type, in the matching slot;
   b. drop sinks unless this is the final link;
   c. drop any whose *other* object preconditions are unsatisfiable in `sim`;
   d. pick one; bind the dependency (object → force the id; value → record only);
   e. fill remaining args as normal; apply via `adapter.apply`; record the edge.
4. Return the steps.

Chains contain **no invalid steps** — an errored action produces nothing, so it cannot be
a link. Distractor invalids remain the outer generator's job.

### Step record

Existing keys are unchanged, so downstream code keeps working. Two are added:

```jsonc
{
  "action": "send_message", "tool": "chat_send_message", "kind": "write",
  "open_ended": false, "objects": {...}, "args": {...},
  "expect_error": false, "entity_id": "m_041",

  "depends_on": { "offset": -1, "via": "object", "param": "chat_id" },
  "produced_value": null            // scalar internal producers only; else null
}
```

`offset` is **relative**: `-1` means "the immediately preceding step", `-2` the one before
that. Relative because the chain does not know where it will be spliced — and unlike a
positional index it stays correct after splicing, so the caller has nothing to renumber
and there is no way to misread it as a global position.

## 5. Adapter changes

`ChatAdapter.apply` already accepts a forced `object_id`, so object binding needs nothing
new. Two additions:

- `Outcome.value: str | None` — the readable outcome of an internal read (`get_user` →
  the handle; `read_messages` → a short rendering). `None` for writes and for external
  reads.
- `_args` must accept a pre-bound value arg rather than always sampling, so a future
  variant can pin content if we ever want it. Not used by v1 (value edges stay filler).

## 6. What this does *not* do

- No placement, interleaving, or turn splitting.
- No changes to `author.py` yet. Value edges will need an authoring instruction ("step 4's
  message must carry what step 2 returned") and a content-obligation output — that is the
  next piece, and it should generalise the existing `_delivery_rules` rather than sit
  beside it.
- No changes to the reward. Object edges are already covered by `state_diff`; value edges
  are unverified until authoring lands. **Chains built before then are structurally sound
  but their content is ungraded** — worth knowing before drawing conclusions from any eval.

## 7. Risks

1. **Cascade.** A chain fails as a unit: miss link 1 and every later fact is unreachable.
   Expect higher variance on chained tasks; keep `length` small (2–3) until measured.
2. **Weight shifts to the weakest verifier.** A value chain is only checked by `state_diff`
   for *placement* ("a message landed in chat X"); its payload rests entirely on the judge.
   Entity chains stay fully deterministic — keep them as the backbone.
3. **Judge cost grows sub-linearly, not linearly.** `judge_open_ended` makes **one** call
   per task no matter how many obligations it carries: the items are rendered into a single
   prompt alongside one copy of the transcript. Since the transcript dominates the token
   count, an extra obligation costs a few lines, not another call. The earlier worry that
   "judge cost scales with value edges" was overstated — worth measuring, not worth
   designing around.
4. **Degenerate chains.** `send_message → reply_to → reply_to → …` is legal and boring; the
   no-immediate-repeat bias mitigates but does not eliminate it.

## 8. How it will be tested (offline, no LLM)

- Requested length is always met, for lengths 2–6 across many seeds.
- Every link's `depends_on` really references the previous step's output, and object edges
  bind the produced id verbatim.
- Sinks appear **only** at the final position.
- No invalid steps inside a chain; the generation invariant (`outcome.error == False`)
  holds at every link.
- `sim` advances so that a faithful replay of the chain reproduces the expected state
  (score 1.0), and the canonical signature keeps that true when the chain is preceded by
  an unrelated create (the id-drift case).
- Spec round-trip: every action has `produces`/`consumes`, and the producer/consumer index
  built from the spec matches the table in §1.

## 9. Resolved: `shape`, not an exclusion list

All internal reads stay chain producers. What differs between them is not whether they can
produce, but whether the resulting obligation can be checked cheaply:

All internal reads stay chain producers. Excluding collection producers would have thinned
the graph badly — without `read_messages` able to continue a chain, most chains collapse to
`send_message → reply_to → reply_to …`. What differs between them is not whether they can
produce, but how well-grounded the resulting obligation is:

| outcome | example | what the author can state |
|---|---|---|
| **scalar** internal | `get_user` → `{"handle":"praman"}` | an obligation about a value we already know |
| **collection** internal | `read_messages` → 20 message objects | must invent the specificity ("quote the one about the embargo") |
| **external** | `deepwiki_*` | must supply a gold from its own knowledge |

### All content obligations are graded by the judge in v1

`verify.py` has exactly three verifiers — state F1, tool-call schema, and the LLM judge.
There is **no deterministic content check**, and the authored obligation schema
(`{question, ground_truth, judge_hint}`) has no field through which the author could
request one. The author's only verification lever is the judge hint. An "exact substring"
fast path would need three new pieces (a `check` discriminator on the obligation, a
content verifier in `verify.py`, and authoring instructions for choosing between them) and
is **explicitly out of scope for v1**.

It is also not free of risk: letting the authoring LLM choose the *verifier type* is the
same failure class as letting it choose the gold. If it emits `contains: "praman"` but
writes prose asking for "the designer who owns onboarding", an agent answering "Priya" is
correct and scored wrong. Deferred, not rejected — revisit if judge cost becomes binding.

### This also closes a gap that predates chaining

Message **text is verified nowhere today**. `adapter.signature` excludes it by design, and
`verify.py` has no text check outside the judge, which only ever sees authored DeepWiki
items. So if a prompt says send *"sounds good"* to the launch chat and the agent sends
*"ok"*, `state_diff` confirms a message landed and nothing notices the content is wrong.

Routing every content-bearing step through an authored judge obligation therefore fixes an
existing hole, not just the new chain case — a good reason to accept the cost in v1.

**Where an obligation is required vs optional.** The generator marks the steps whose
content is *structurally* load-bearing (value edges); the author **must** emit an
obligation for those. It **may** add obligations for other steps where its own prose
constrains the content. That sets a floor without capping the ceiling, and keeps the
author from silently skipping the one case the generator knows matters.

### What `shape` and `produced_value` are for, then

Not verification. Two things that need no new verifier:

1. **Grounding the author** — showing it `get_user(u_priya_raman) → "praman"` lets it write
   an obligation about something real, rather than guessing what the step returned. This is
   the same defect that produced unanswerable DeepWiki golds.
2. **Validating a claimed gold at generation time** — if the author gives `"praman"` as the
   gold for an internal step, assert that string actually occurs in the seed. That catches
   a hallucinated gold automatically, before any eval runs. External golds still need the
   human pass; internal ones stop needing it.

`produced_value` is populated for **scalar internal** producers; collection and external
leave it `None`. `shape` distinguishes the two `None` cases, which are different
situations: a collection gold is knowable but unwieldy, an external gold is unknown.
