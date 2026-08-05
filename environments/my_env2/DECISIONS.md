# Decisions

Every place `NEW_IMPLEMENTATION_PLAN.md` left a choice, and what was chosen. `[OPEN]` items
from the plan are answered first; then the interpretations; then what is deliberately not built.

## The plan's `[OPEN]` items

**Does the shipped task carry v3 only, or all three prompt versions?** All three, over one
`(seed, expected)` pair. It costs two extra calls per task and yields matched triples that
differ in nothing but how explicitly the work is specified — which is the only way to attribute
a score gap to specification rather than to authoring noise. `ChatConfig.level` picks which one
an eval serves. See `taskset.py`.

**Does the judge receive the final state, the transcript, or both?** Both, but they are not
equal. `verify.transcript` shows the full rollout as *context only* and then a DELIVERED OUTPUT
section — the messages the agent sent, plus its final reply — and the judge is told to grade
against that section alone. Every judge item is about delivery: information that had to reach a
message or the reply. An answer sitting in a tool result the agent never passed on is not a
delivered answer. The full rollout is still needed to tell a retrieved answer from a guessed one.

## Stage 1

**The step record's shape.** The plan lists `objects`, `args`, `expect_error`. A symbolic step
has three kinds of param that are filled by three different things at three different times —
entity refs (bound at replay), content (authored at Stage 7), carries (supplied by the agent and
checkable only by a judge) — so they are three fields, not one `args` dict every consumer would
have to re-split. `expect_error` is gone: it existed for the old generator's deliberately-invalid
draws, and a dependency chain has none, because a failed action produces nothing to chain from.

**Symbol names are unique within a task, not across tasks.** The plan asks for the latter. Names
like `$chat_0` are worth keeping because the authoring model reads them, and a task-id prefix on
every placeholder buys nothing: no code path merges two sequences, records are keyed by task id,
and so are cache entries. `Sequence.task_id` travels with every artifact so the association is
never implicit.

**Rollout-created entities are named `$new_chat_0`, not `$chat_0`.** The authoring stages must
bind seed placeholders and only those. A name that says which is which removes that whole class
of mistake instead of relying on an instruction being followed.

**`ChainBatch` keeps neither `seed` nor `expected`.** Stage 1 returns a `Sequence`; Stage 6
produces a `Replay`; the `TaskRecord` is what carries both states. Nothing has a field that is
empty for half its life.

**Seed entities are reused across steps (`p_reuse`, default 0.5).** The stateful walker sampled
from a live world, so two steps naturally touched the same thing. Minting a fresh placeholder
per unbound ref would have removed that, and with it any prompt that says "that chat" and means
something — the previous pipeline's anaphoric difficulty rung was abandoned for exactly this
reason.

**A single-link thread may open with a sink.** `mark_read` needs a chat with unread history, and
nothing produces one, so it can never be a dependent link — without this it could only ever
appear as a distractor. `DEFAULT_CONFIGS` therefore carries a third, one-link thread: the
mechanism is useless unless some thread is configured shallow enough to use it.

**`links_per_thread` and `longest_chain` are both reported, because they are different things.**
A thread's links can all hang off a single foreign source, which is a fan-out two deep however
many links it has. The plan asks for realized values "usable for later difficulty analysis", and
regressing difficulty on link count while calling it depth would answer a different question.
Over 500 sampled sequences at `p_cross=0.9`, the two disagree for 85% of threads.

**A list-valued object slot binds a list of symbols, and that code is unreachable in this spec.**
The plan requires it implemented, and it is (`create_chat.member_ids`). Nothing in this spec
produces a `user`, so no object edge ever feeds a `many` slot and `member_ids` is always minted
from the seed instead. Feeding it would take an action that creates a person, which this
environment does not have.

## Three guards that were not in the plan

The previous pipeline was measured, and 8.7% of its write links (59 of 675) wrote a fact that was
already true — indistinguishable, to the reward, from doing nothing. Two structural guards and
one measured gate replace that:

1. **No repeated write pair.** An action declaring `meaningful_when` is never applied twice to
   the same entity. That was every duplicate `add_reaction`.
2. **`requires_history` actions never consume a rollout-created entity.** `mark_read` on a chat
   the agent created marks nothing; `read_messages` on it returns nothing a later step could
   carry. Declared per action in the spec, so the rule stays generic.
3. **Replay drops a task containing a no-op write, or a read that came back empty.** The first two
   hold by construction; this one measures. A predicate over args would have to reimplement each
   tool's effect logic in a second place and the two would drift, so replay compares the signature
   before and after every step instead, and inspects what each read returned. Over 150 stub-world
   tasks: 0 no-ops in 576 write steps, 0 empty reads.

The empty read matters as much as the no-op write and is easier to miss. Guard 2 only excludes
*rollout-created* entities; nothing stops the authoring stage binding a seeded chat that happens
to have no history. Nothing errors, the state diff has nothing to say about a read either way, and
the judge item built from it would demand information that does not exist — a graded requirement
no agent could satisfy.

**A parameterless action is emitted at most once per task.** An action with no ref and no content
param has exactly one possible invocation, so a second `list_chats` is the same call again.

## Stage 0 — reference modes

**Modes are declared in the spec and resolved by the adapter.** The spec carries the predicate,
its params, a prose `phrase`, and `readable_via`; the adapter implements
`resolve(state, mode, params) -> [entity_id]`. That keeps the pipeline's own code free of any
knowledge of what a chat is, and puts the Boolean predicate somewhere it can actually be
evaluated.

**Every mode is globally scoped.** No mode names another entity. A mode like "the newest message
in chat C" would need C resolved first, which makes uniqueness undecidable without recursion and
makes `phrase` a nesting problem. Twelve modes, four per entity type, all self-contained.

**Superlative modes require a strict maximum.** "More reactions than any other" returns nothing
on a tie, rather than picking a winner the agent has no way to pick.

**`readable_via` names the actions needed *in combination*, not one action that exposes the
property outright.** Reading a handle takes `get_user`, but finding whose handle to read takes
`list_chats` first, so both are listed. The field is load-bearing under that reading and merely
decorative under the stricter one, since almost nothing in this environment is observable in a
single call.

It is also why `sender_id` was added to the message view in `servers/tool.py`: display names
collide on purpose, so without it a prompt could describe an author ("whoever pushed back on
that") the agent then has no way to identify, and the task would be unsolvable rather than hard.

## Stage 4 — the model proposes, the adapter guarantees

The authoring model picks **which mode** suits an entity, and nothing else — it is not asked for
params at all. The adapter derives them from the state, and a mode is accepted only when
`resolve(...) == [target]`; modes are tried in the model's preferred order first, then in declared
order.

That division was not the original one — the model supplied params and they were kept whenever
they resolved — and the reason for changing it is worth recording, because "it resolved" looked
like sufficient evidence. A proposal that quoted an entire message back verbatim resolved
perfectly, and the resulting v2 prompt read: *"the conversation where Before we start the
migration, does the repo primarily use Maven or Gradle? We should document current state first.
came up"*. Resolving and being usable are different properties, and only the first is checkable.

**Modes are declared most-indirect-first**, because declared order is the fallback order. The first
run put `user_by_handle` first and every reference in every task came back as "the person whose
handle is @…", which is not a reference at all — it is the id with different punctuation.

Stage 9 strips ids out of the prompt entirely, so an entity without a working reference does not
produce a harder task — it produces an unanswerable one. This makes Stage 4 total, and it fails
loudly (rather than silently shipping) when a world is too uniform to describe.

`mode_params` verifies its own answer before returning it, so a non-None result *is* a resolution
and no caller has to re-check. Deriving without verifying was not enough: a superlative mode has
no params to get wrong and so would claim to fit any entity at all, and a display name derived
from the target may well be shared with someone else.

Params that come from the model are arbitrary JSON — a number where a string belongs, a null, a
nested object — so anything a resolver throws on them is treated as a rejected proposal. Letting
it propagate would abandon every task already built in the batch, since the file is written at the
end.

Where a mode needs a distinctive phrase, the span of real message text used is **not the shortest
unique one**. That was the first rule and it was wrong: any span containing a unique span is itself
unique, so the shortest is usually a single word, and "the message about Before" is a worse handle
than "the message about the backfill job times out" however much less it quotes. Three criteria
decide it instead — don't run across a sentence boundary, open on a real word rather than an
article or a preposition, and sit near four words, which is about where a quote starts reading as
a topic.

## Stage 5 — population

Filler is folded in **one entity at a time**, and each addition is kept only if every reference
condition still resolves to exactly its own entity — the plan's "checked programmatically as each
entity is added", taken literally. Checking once at the end would make the failure mode *lose the
batch* instead of *drop one message*. What was dropped, and why, is recorded in the task's
warnings rather than discarded. Filler messages are added in clock order rather than list order,
because `build` validates a reply against the clock: a child listed before its parent would be
rejected on its own and accepted as part of the whole, silently unthreading filler conversations.

**Stage 5 is shown the world in the draft's own vocabulary, not the built state's.** This is the
difference between filler that can go anywhere and filler that cannot go anywhere useful. A draft
refers to people and chats by local keys it invented (`u2`, `c1`); the built state has only real
ids. Shown the latter, every addition naming an existing chat is rejected, and the only filler that
survives is new people talking in new rooms — which hides nothing, since the task's own chats then
contain task-relevant traffic and nothing else.

**Its additions come back under `new_users` / `new_chats` / `new_messages`, and a reply containing
no new key is rejected.** Asked to add to a world, a model hands the world straight back: the first
run returned the core draft verbatim, every entry keyed to something that already existed, so every
one was dropped as a duplicate and the stage yielded nothing while appearing to have run. Separate
keys put "these are additions" in the shape rather than only in the instructions, and the emptiness
check turns the remaining failure into a correction round instead of silence.

**The acting user's handle is reserved (`@you`) rather than authored.** Letting the model choose one
produced the same failure repeatedly, and it survived the correction round: it would pick a handle
for itself and then declare a colleague with the same one, because it reads `users` as "everyone,
including me". Reserving a handle removes the collision instead of asking for it not to happen. The
display name is still authored, since a named actor is what makes the world read as somebody's.

Draft messages carry an `order` field and the seed's clock is built from it, so filler history
**interleaves** with the core history rather than being appended after it. With filler landing in
existing chats, that is what keeps `read_messages` from returning the real conversation first and
the padding last, and what lets "the latest thing they posted" mean something other than the most
recent filler.

Three seed invariants are enforced in code rather than asked for, because all three are
load-bearing and asking is unreliable: **the acting user is a member of every chat** (`list_chats`
shows only the actor's chats, so anything else is invisible and therefore unreferenceable), **the
acting user has no seeded reactions** (one would make a task's own `add_reaction` a no-op), and
**no two handles collide**, including with the actor's own.

That last one is a rejection, not a rename. Handles are the one thing this environment promises
never collide — it is what makes a person nameable when display names do not — and renaming the
duplicate would honour the letter of that while producing a world nobody asked for. In practice the
collision that fires is the draft inventing a second copy of the acting user. Undeclared and
non-member reactors are rejected on the same grounds: reactions decide `message_most_reacted`, which
needs a strict maximum, so quietly dropping one can turn an intended clear winner into a tie and
cost that message its reference. The actor is the single exception — removed rather than refused,
because the no-seeded-reactions rule is one the draft was never told about.

## Stage 8 — what gets judged

Judge items are computed in code; only their expected answers and hints are authored. Two things
qualify:

- a **carry** requirement, where a value edge means one step's message must contain what an
  earlier step returned — the state diff sees the message exists but never what is in it;
- a **read nothing carries**, whose answer has nowhere to land but the agent's reply.

The second covers internal reads as well as external ones. Restricting it to external answers left
about 15% of internal read steps reaching neither reward component: a read has no state effect, so
without a judge item there is nothing about it to score, and the prompt would be asking for work
that is invisible to both halves of the reward. `tests/test_pipeline_offline.py` pins the resulting
property — every step reaches at least one component.

Authored free text is deliberately *not* judged. The author invented it, so checking that the
agent reproduced it word for word measures obedience to phrasing — and v3 removes the phrasing on
purpose.

**A distractor step is labelled as one *in addition* to its kind, never instead of it.** An aside
still writes to the environment and is still in `expected`; an author shown only "distractor" drops
it, and the agent then loses recall for obeying the prompt — the very failure this design was
supposed to have removed.

**Where each answer goes is decided from the plan, not by the author.** An author free to pick a
destination invents a message the plan does not contain, and the state reward then penalises the
agent for obeying the prompt. This was a measured failure of the previous pipeline.

For an internal source the expected answer is grounded in what the read *actually returned* at
replay, which is why `Replay.observed` exists. For an external source the model supplies it from
its own knowledge.

## Reward

**Two components, as the plan specifies.** The previous env also scored tool-call
well-formedness; that is gone. Weights are 0.6 `state_diff` / 0.4 `delivery`. The deterministic
half stays the majority because it is exact and cannot be talked into agreeing. It is not larger
than that because value edges are the more common edge kind these sequences produce — 761 value
against 564 object edges over 400 sampled tasks — so 0.7/0.3 would under-weight most of what the
tasks actually ask for.

**A judge that misbehaves is not charged to the agent.** A verdict array whose length does not
match the item count raises, rather than counting the missing ones wrong. That follows the
framework's own convention in `verifiers/v1/judge.py`, and the alternative silently converts a
judge failure into a low score for the model.

**Per-turn diffs are recorded and not scored.** Every fact in them is already inside the
`state_diff` comparison, and a milestone reward can only ask whether a turn's facts are all
present — recall with no precision term — which would dilute the one half of the F1 that punishes
an agent for changing things nobody asked about. They are persisted, and the CLI prints them,
because they say which turn a failed run stopped matching at.

## Authoring mechanics

**v2 and v3 must name no action, no tool, and nothing they are supposed to describe.** All three go
into the forbidden list handed to the author, and all three are checked afterwards. An id hands the
agent the resolution step. A tool name hands it the call, turning a request from a colleague back
into a function invocation — the scaffolding v2 exists to remove. And a display name or a chat title
hands back the answer to a description: the first v3 output read *"Alice Rivera (the author of the
timeline message that proposed a feature freeze on Aug 10)"*, which is worse than either half alone.
Whatever the assigned reference itself says is exempt, since where the chosen mode *is* the name,
the name is the description.

v3 is also given the reference list, which it originally was not. Told only to raise the level of
abstraction and to keep every reference resolvable, it did the sensible-looking thing and started
naming people to be safe.

**A `null` from the model means "not applicable", so the field's default stands.** Writing out
every optional key as `null` is what a model does when it follows a schema conscientiously
(`"reaction_emoji": null` on a message nobody reacted to), and treating that as a type error spent
a correction round per task on a reply that was not wrong.

**One corrective retry, and nothing is ever patched by us.** A reply that parses but fails its
stage's contract is handed back its own rejection message once; a second failure drops the task.
The plan defers the retry policy, and this is the minimum that makes the pipeline function:
without it a weak model's yield is zero, and with anything more elaborate the pipeline starts
repairing tasks whose prompts then describe a world other than the one shipped.

**The cache is keyed by task id, stage, model and a hash of the exact prompt** — not by task id
alone. Editing a stage's prompt and silently getting the old answer back is a much worse failure
than re-paying for a call whose prompt did not change. Every call is written out in full, prompt
included, so a run can be audited without re-running it.

**Temperature is left unset.** The gpt-5 family rejects anything but its own default, and the
variety here comes from the sequences rather than from sampling noise.

**DeepWiki tool guidance lives in the spec's `returns` strings.** The previous pipeline carried a
hardcoded dict explaining which of the three tools can answer what. The spec is the source of
truth and the renderer already shows `returns`, so the guidance belongs there — and an
environment with different external tools then needs no code change.

**The taskset has no live-generate mode.** A world invented during an eval could not have had its
references checked for uniqueness first, which is the one thing the whole design rests on.

## The ladder — a fourth rung, and what the rewrites got wrong

**The judge specification is rewritten at every rung, not authored once.** It used to be authored
alongside v1 and shipped unchanged to all three levels. But v1 is the rung that names steps and
ids, so that is the language the items were written in: over twelve tasks the hints read like
*"Look at the message the agent sent to chat c_001 (step 4)"* — handed to a grader reading an L3
rollout in which nothing is called `c_001` and there are no steps. Each rewrite stage is now given
the rung below's items and must restate each one's `expected` and `hint`. `TaskRecord.judge` is
keyed by level as a result.

`id`, `requirement` and `delivered_in` are **not** rewritable. An author allowed to restate the
requirement weakens one; an author allowed to choose the delivery target invents a message the plan
does not contain, which the state reward then punishes the agent for obeying. That was already a
measured failure of the previous pipeline and there was no reason to reintroduce it here.

**A description introduces a thing once; it is not a substitution token.** The old instruction was
"replace every identifier with the description supplied for that entity", and the model did exactly
that: 40 of 81 phrase uses across twelve tasks were the same description pasted again. In t1, v1
named `c_002` three times and *also* said "in that chat" once — v2 produced the full phrase four
times, having de-anaphorised the one place v1 had a pronoun. In t8 one phrase appears five times.

That is not only ugly. `chat_only_with_unread` reads "the one conversation you still have not caught
up on", and t1's third step marks that conversation read — so the third and fourth uses are false.
`stale_references` re-resolves every reference against `expected` and the rewrite stages are told
which ones the work invalidates, so such a thing can be introduced before the step that breaks it
and referred back to afterwards. The rule names its replacements ("that conversation", "there",
"the same thread") rather than only prohibiting the repeat, because a prohibition without a
replacement is what produced the de-anaphorising in the first place.

**A fourth rung rather than a stricter third.** L3 was asked to raise the level of abstraction and
did the locally sensible thing: it added a goal sentence and left the step sequence underneath it
intact, still narrating hand-offs ("retain the full array of message views returned for later use")
and still dictating quoted questions. Tightening L3 would have moved the rung rather than added
one, and the L1→L2→L3 numbers already collected would no longer be comparable. L4 keeps L3 as it
is and asks for three further things: fold actions that exist only to feed each other into one
request, drop hand-off language entirely, and stop dictating content — say what a question needs to
find out instead of quoting it. A repository *name* still has to survive verbatim, because that is
what the expected answer is keyed to; the question around it no longer does, which is exactly why
the judge items have to be restated at this rung.

**Sequencing connectives are checked at L3 and L4 only.** `_complaints` never noticed that 6 of 12
v3 prompts chained their steps with `; ` or ` then ` while passing every other check, because it
only looked for line-start enumeration. v2 is prose and is allowed to read sequentially, so the
check is gated per rung rather than applied everywhere.

**The judge grades over the whole rollout.** It used to be shown the full trace as "context only"
and told to grade against a delivered-output section alone. The instinct behind that is right — an
answer sitting in a tool result the agent never passed on is not delivered — but the framing made
the final reply the de facto target, when most items are about information landing in a message
partway through. The judge is now told to use the whole trace, with both halves stated explicitly:
the information has to appear where the item's hint says, *and* it has to match what the tools
actually returned, since that is the only way to tell a retrieved answer from an invented one. The
delivered-output section survives as an index into a long transcript, not as a narrower target.

## Deferred — tracked, not built

- **Filler entities carry no reference properties.** Only task-relevant entities are unusually
  specific, which leaves a shortcut: an agent can find targets by noticing which entities are
  conspicuous rather than by resolving anything. Closing it means generating reference properties
  for filler at comparable density, including near-misses that satisfy a core condition partway.
  The plan defers this; it remains the clearest known weakness of the resulting task set. Stage 5
  putting filler *inside* the task's own chats narrows it — the target chat is no longer the only
  one with substance in it — but the target entities themselves stay the sharpest things in the
  world.
- **Discoverability budgets.** Nothing bounds how many queries resolving a reference may cost.
  `user_most_messages` and `message_most_reacted` require reading every chat.
- **A real validation and retry policy** beyond the single corrective round above.
- **An automated ambiguity check on v2 and v3.** Two cheap checks do run — a leaked seed
  identifier, and v3 still enumerating steps — but they are recorded as warnings, not enforced.
- **External content drift.** A DeepWiki answer can change under a stored expectation. The
  accepted handling is periodic re-verification by a human or a stronger model.
- **Reference uniqueness across a rollout.** It is asserted against the seed only, per the plan.
  Authored content that repeats a phrase some reference depends on is recorded as a warning,
  since the agent reads before it writes and the description is only needed at the start.
