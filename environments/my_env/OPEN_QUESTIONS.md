# Open questions

Known gaps in the pipeline, each with the in-repo evidence for it, why it is still open, and
what a fix would touch. Sections 1–6 are ordered by how much they distort a score today; the
last section records directions considered and deliberately deferred, which are a different
kind of thing.

Nothing here is a blocker for the next milestone (action-chain generation, `CHAIN_PLAN.md`);
items 1–3 are the ones most likely to make an eval number mean something other than what it
looks like.

## 1. An incidental write collapses precision

`state_diff` is an F1 over state facts, and a single plausible-but-unplanned write can
contribute more facts than the entire intended task.

**Evidence.** `samples_v3/rescore/eval_results.md`, L4/L5 idx4: the agent produced all 3
expected facts, then also called `chat_mark_read(c_003)` — the plan has
`chat_read_messages(c_003)`, a read. `c_003` holds 7 messages, so that one call added 7
unexpected `read` facts and dropped `state_diff` from 1.00 to 0.46. The intended work was
done perfectly.

**Why it is open.** The asymmetry is real, not a bug: precision is what makes the reward
penalise extra actions at all, and weakening it re-opens that hole. But `mark_read`'s fact
yield scales with chat size while every other action yields 1–4, so the penalty is set by
which chat happened to be sampled.

**A fix touches** `adapter.signature` (cap or normalise a single action's fact yield — e.g.
one `read` fact per *chat* marked rather than per message) or the reward composition (a
separate unexpected-writes term instead of folding it into precision). Either changes every
existing score.

## 2. Single-fact tasks are all-or-nothing

Nothing requires a sampled plan to have a minimum expected state delta, so a task can turn
on one fact and the 0.5-weighted component becomes binary.

**Evidence.** `samples_v3/rescore/eval_results.md`, L5 idx2: the expected delta is the single
fact `('react','m_035','u_me')`. The agent reacted to `m_023`, so F1 = 0.00 and the task's
total fell to 0.32 — indistinguishable from doing nothing at all.

**Why it is open.** A minimum-delta gate was considered and deliberately not built while the
sampling knobs were still moving. Action chains should reduce the rate on their own, since a
chain contributes several linked facts.

**A fix touches** `generate` (reject or resample a plan whose expected delta is below a
floor) — cheap and offline, and worth pairing with the gold-replay soundness check
(`verify(initial) == 0.0`, `verify(gold) == 1.0`) that also does not exist yet.

## 3. Open-ended golds the plan's own tool cannot answer

The plan fixes *which* DeepWiki tool an open slot uses. `read_wiki_contents` returns wiki
prose and `read_wiki_structure` returns topic titles; neither states repo metadata. When the
authored question asks for metadata anyway, a correct agent reports "not stated" and the
judge correctly scores it 0.

**Evidence.** 3 of 5 tasks in `samples_v3`:

| idx | tool the plan picked | what the authored question asks for |
| --- | --- | --- |
| 1 | `read_wiki_contents` | primary language + license |
| 2 | `read_wiki_structure` | top-level files and directories |
| 2 | `read_wiki_contents` | the exact one-line description at the top of `README.md` |
| 4 | `read_wiki_contents` | primary language + maintainers |

**Why it is open.** `author._OPEN_GUIDANCE` already spells this out per tool, including
"NEVER ask for licence, stars, maintainers or primary language". The guidance is present and
was ignored, so more prose is not the fix — this needs a check.

**A fix touches** `author.py`: validate the authored question against the slot's tool before
accepting the task (a cheap classifier call, or reject-and-retry on a keyword blocklist for
the two `read_wiki_*` tools), and drop the task if it fails twice, exactly as `_attempt`
already does.

## 4. Nothing checks a task is solvable

An authored prompt can carry two constraints that pick different entities. The rewrite
rungs are told to keep every reference resolvable to exactly one entity (`author.py`
invariant 4), but no pass verifies it, so an underdetermined prompt is indistinguishable
from a harder one.

**Evidence.** `samples_v3/authored_tasks_l3.jsonl` idx0 asks for a reply to *"the oldest
unread message in the launch channel that reads 'If it slips we have to redo the press
embargo.'"* In that seed **all seven** messages in `c_001` are unread by `u_me`, so the
ordinal points at `m_001` while the quote pins `m_004`. The plan's target is `m_004`; an
agent that trusts the ordinal loses the fact.

**Why it is open.** A solve-check gate was considered and deliberately excluded — it needs
either a reference solver or a rollout per candidate task, and the whole point of the ladder
is that prompts stay cheap to produce.

**A fix touches** either `author.py` (a validation pass that re-resolves each reference
against the seed) or the eval loop (treat a task no strong model can solve as defective
rather than hard — the empirical-gating approach). Both are larger than the ladder itself.

## 5. The name of a created chat is unverified

`chat_create_chat(name=...)` reaches the prompt verbatim, and no pass checks it. An agent
that creates the chat with the right members but the wrong name, or no name at all, scores
identically to one that gets it right.

**Evidence.** `adapter.signature` keys a created chat by its member set and an occurrence
index only; `chat.name` is read in exactly one place in the scoring path (`taskset.py`, as a
display label for messages the agent sent). Verified offline: `name="retro"`, `name="Retro"`
and `name=None` all produce the identical delta `('new_chat', ('u_maya','u_me'), 1)`, and
expected-`retro`-vs-actual-unnamed scores `state_diff` 1.000. `kind` silently flips
group→dm with the name absent, and is likewise unchecked. 184/400 sampled `create_chat`
calls carry a name; 2 of the 5 frozen `samples_v3` tasks do.

**Decision taken.** The name stays **out** of `state_diff`. A chat name is content, and the
generator picking it from a hardcoded four-word list (`adapter._CHAT_NAMES`) is plumbing, not
task design — the authoring LLM should choose it, which means it cannot be a constant the
generator knows. Content is the judge's business.

**Consequence for `CHAIN_PLAN.md`.** `create_chat.name` must **not** become a chain value
slot while this is true. Per §2 a value edge keeps its sampled filler, so `expected` would
carry the filler name while the prompt asks for a name derived from a read — a correct agent
would then be graded against the wrong gold, which is worse than not grading it.

**A fix touches** three small pieces, none of them new plumbing — the judge already receives
the full rollout *and* `trace.state`:

- `author.py` — choose the name, and emit an obligation for it.
- `verify._OPEN_ENDED_PROMPT` — it currently says to grade the delivered-output section only
  and to use the full rollout "never as the answer itself". That rule was written for
  *answers*; for a state change the state itself is the delivery, so the prompt needs to
  cover both.
- `taskset._transcript` — render chats created during the rollout (name + members) into the
  graded section, alongside the messages block.

The existing obligation shape `{question, ground_truth, judge_hint}` probably suffices, so
two decisions are worth making when this is built: whether a state-change obligation shares
the `open_ended` reward (it would dilute the DeepWiki items, since the reward is one fraction
over all of them) or gets its own; and that a wrong name will then cost less than a wrong
member set, because membership is deterministic at weight 0.5 and the name is a fraction of
weight 0.3.

## 6. `create_chat` does not validate `member_ids`

The precondition is declared `enforced: false` in `action_spec.json`, so the tool accepts
member ids that do not exist and silently creates a chat containing a nonexistent user.

**Evidence.** `samples_v3/rescore/eval_results.md`, L1 idx0: the agent passed
`member_ids: ["maya"]` — the *handle* where the *id* `u_maya` was required. The chat was
created, and `state_diff` scored 0.91 rather than flagging an impossible chat.

**Why it is open.** It is a soundness gap in the mock app rather than in the pipeline, and it
partly reflects a real product decision (the tool is permissive on purpose). But it means a
handle/id confusion is scored as a near-miss instead of an error.

**A fix touches** `servers/tool.py` (return `{"error": ...}` for unknown members) and
`action_spec.json` (flip `enforced` to `true`), which makes `create_chat` invalidatable and
therefore eligible for the generator's `p_invalid` draw — a behaviour change to the sampler,
not just a validation tweak.

## Deferred directions

Considered, judged worth doing eventually, and deliberately not started. Recorded with the
reasoning so the decision does not have to be re-derived.

### Automatic action abstraction (compound actions in the spec)

**The idea.** A BPE-style merge over the action surface: enumerate pairs of elementary
actions, ask an LLM whether each pair is a natural single intent, merge the accepted ones into
a compound action in `action_spec.json`, and repeat for ~5 rounds to reach compounds of
degree 5.

**The ceiling it targets is real.** With 11 primitives every task is "do 8 small things" and
never "do 2 meaningful things", and uniform sampling over them produces plans with no
narrative — react to a message, look up a user, mark a chat read, create a chat.

**Why it is deferred.**

1. *It does not create the dependency that motivated it.* The example was
   `list_chats → read_messages`, which has no data dependency: the chat id already exists and
   `read_messages(c_003)` is directly executable. The dependency lives in the agent's
   **information** state, which nothing in the pipeline represents. A compound emits both
   steps but the prompt still hands over the id, so nothing forces the discovery — only
   withholding the id does, and `author.py` invariant 6 already does that at L2 and above by
   banning raw ids outright (discovery reads: 7 at L1, 20 at L2, 23 at L4). A side note that
   falls out of this: L1 is the only rung with no discovery at all, which is one reason it has
   been an unstable baseline.
2. *The merge rule loses its justification.* BPE works because merges are driven by corpus
   frequency — it discovers the abstractions that are actually common. There is no corpus
   here, so an LLM would be supplying a prior with nothing empirical behind it. The version
   that keeps the justification intact is corpus-driven: collect traces of a strong model
   succeeding in this app, count the action bigrams that actually co-occur, merge the frequent
   ones. That needs eval data that will exist after the chain milestone, not before.
3. *Soundness depends on what a compound is, and that must be decided first.* Everything
   sound about this pipeline rests on the generator driving the real tools so that `expected`
   is genuinely simulated. If a compound decomposes into its primitives at execution time it
   is a named macro, the verifier is untouched, and it buys a sampling distribution. If
   instead a compound gets its own LLM-written effect semantics, those are unverified prose
   and `expected` stops being ground truth. Only the first is safe.
4. *There is no stopping rule.* 121 ordered pairs in round 1; if 15 merge, round 2 judges 676;
   by round 5 that is thousands of LLM calls producing mostly near-duplicates. BPE bounds this
   with a frequency cutoff and there is no equivalent here. A degree-5 compound is also an
   entire task (tasks run 3–10 actions), at which point the spec has absorbed the generator.

**What form it should take when revisited.** If the goal is *this* environment's task quality,
hand-curation wins outright: 121 ordered pairs is an afternoon's work, and a person judges
"do these combine naturally" better than a generic LLM, because the answer depends on this
app's semantics and on the scoring constraints. If the goal is the **generic method** — the
README frames my_env as a reusable pattern — then automated discovery is the more valuable
artifact, since it ports to an action surface too large to curate by hand. In that case 11
actions is a good prototyping ground *precisely because* all 121 pairs can be hand-labelled
first, and the deliverable is a **merge rule validated against that answer key**, not the
compounds it emits.

**Cheaper steps that capture much of the value, in order.**

- Hand-write two or three compounds that are genuine single user intents.
  `read_messages + mark_read` ("catch up on a chat") is the obvious first, and it retires the
  trigger case for §1 above: idx4 lost 0.54 because the agent conflated exactly those two
  actions. It removes the commonest trigger, not the underlying precision asymmetry.
- A hand-written coherence prior over action bigrams, biasing the sampler away from incoherent
  plans. No LLM, no spec change, no verifier impact.
- A `discover: true` marker on a step's object, so the generator *declares* that an id must
  not reach the prompt rather than relying on an authoring invariant to imply it. That makes
  the discovery dependency measurable, which it currently is not.

Sequenced after `CHAIN_PLAN.md`: a macro library is a distribution over sequences, so the
sequence machinery has to exist first.
