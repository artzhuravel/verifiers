# Pipeline review

Every stage of the `my_env2` pipeline, written out one artifact at a time so it can be read
without reading the code that produced it. Two things are here:

- **`01_sequences/`** — Stage 1 for eleven indices. Generated offline: no world, no model, no
  cost. This is what a task looks like before anything has been authored.
- **`02_authored/`** — all twelve tasks from `../samples/tasks.jsonl`, taken apart stage by
  stage: the prompt each authoring call received, what came back, and what each stage derived.
  Includes the ladder for every one of them.

- **`04_offline_exact_prompts/`** — four tasks driven end to end here, so every one of the eight
  authoring prompts is byte-for-byte exact. The world is mechanical and the prose is canned; this
  set exists because two stages' prompts cannot be reconstructed from a shipped task.

**Looking for the prompts? [`PROMPTS.md`](PROMPTS.md)** lists all nine LLM calls in a task's life,
the file holding each, and the constant in the codebase it comes from.

**[`L4_TARGET.md`](L4_TARGET.md)** is why the ladder gained a fourth rung: what L3 got wrong, what
L4 asks for instead, and the same checks run over both.

Otherwise start at [`02_authored/LADDER_INDEX.md`](02_authored/LADDER_INDEX.md) for the ladder, or
[`01_sequences/SUMMARY.md`](01_sequences/SUMMARY.md) to see what the generator emits.

## Before and after

There are two sets of the same twelve indices, and the difference between them is the point.

**`02_authored/` is the BEFORE set.** These twelve tasks were authored before the rewrite stages
changed, so their v2/v3 text is pre-fix output — descriptions pasted per occurrence, judge items
left speaking v1. Each prompt file shows the *current* instruction above that historical reply, so
reading the pair is the before-and-after. Their prompts are reconstructed rather than logged, which
works because every authoring prompt here is a pure function of things the record already stores;
the sequence is regenerated from `idx` and checked against the stored steps first, so a spec change
since would fail loudly rather than produce a plausible fake. All twelve matched.

**`03_live/` is the AFTER set.** The same twelve indices authored through the current pipeline by
`openai/gpt-5-mini`, with every prompt **logged, not rebuilt** — so all eight are exact, stages 4
and 5 included, and it is the only place genuine **correction rounds** appear.

[`MEASURED.md`](MEASURED.md) counts the defects across both. In short: judge drift went from 54 of
56 items to 2 of 84; repeated descriptions halved (L2 51%→27%, L3 46%→22%); and sequencing did not
improve at all, which is the one change of four that did not land.

## Fidelity — what is exact and what is not

| stage | prompt | result |
| --- | --- | --- |
| 2 shared context | **exact** | — |
| 3 world | **exact** | real (the shipped seed; the draft itself is not stored) |
| 4 references | format-faithful, **later world** | real |
| 5 populate | format-faithful, **later world** | real |
| 6 replay | — | real, re-executed |
| 7 content | **exact** | real |
| 8 v1 + judge | **exact** | real |
| 9 v2 | **exact** | real |
| 10 v3 | **exact** | real |
| 11 v4 | **exact** | the twelve pre-fix tasks have no v4 reply — the rung postdates them |

Stages 4 and 5 ran against the *core* world, before padding, and only the padded world ships.
Their prompts are rebuilt with the right blocks in the right order but the workspace inside is
the later one. Both files say so at the top. Everything under "result" is the shipped artifact,
not a reconstruction.

## Which files are prompts

Only the `*.prompt.txt` files and `12_judge_prompt.txt` are prompts — see
[`PROMPTS.md`](PROMPTS.md) for the full list. Each carries the system message and the user message
as the model received them, then the reply.

Everything else is a rendering written for a reader — including the sequence files, whose blocks
are individually tagged `[SENT]` or `[REVIEW ONLY]` so the two cannot be confused. Of the six
blocks in a sequence file, two are prompt content (`symbolic_steps` and `manifest_brief`) and four
are commentary; the shape metrics, the clock grid and the edge table have no counterpart anywhere
in the pipeline, and the model infers the edges only from lines inside the plan block.

The first three blocks of *every* authoring prompt are the shared context. It appears in full
inside each `*.prompt.txt`, and is also pulled out on its own into `02_shared_context.txt`, because
it is identical across all eight calls and worth reading once.

## What each file shows

Per task, in `02_authored/t<n>/`:

| file | what to look at |
| --- | --- |
| `01_sequence.txt` | The plan before any world exists. The **clock** grid shows three threads advancing in parallel and skipping turns; the **dependency edges** section is why this is a chain and not a list; the **REQUIRED** lines under each placeholder are what stop a step being a no-op. Every block is tagged `[SENT]` or `[REVIEW ONLY]` — only two of the six are prompt content. |
| `02_shared_context.txt` | The block prepended to all eight authoring calls. Every word comes from the spec — this is the whole of what the pipeline knows about the domain. |
| `03_world.prompt.txt` | The world being invented to fit the plan, rather than the plan being sampled from a world. |
| `03_world.result.txt` | The workspace that shipped, plus every symbol bound to a real id. |
| `04_references.prompt.txt` | The model is shown each entity and the four modes available for it, and asked only **which**. It is not asked for params. |
| `04_references.result.txt` | The chosen mode, the params the *adapter* derived, the phrase, and a printed `resolve()` proof that it matches exactly one entity. This is the file to read if you want to see the uniqueness guarantee actually hold. |
| `05_populate.prompt.txt` | The one call shown the world in draft vocabulary (`u1`, `c2`) so it can add to an existing conversation. Also the CONDITIONS every addition must preserve. |
| `05_populate.result.txt` | What was rejected and why. |
| `06_replay.txt` | The validity gate. Per step: concrete args, the facts it added, what a read returned. Then the per-turn diffs, then **exactly what the deterministic reward will look for**. |
| `07_content.*` | Free text, written last, because `signature` excludes it and the expected state is already fixed. |
| `08_concrete_plan.txt` | The plan once the world exists. Every rung is held to this. |
| `08…11_prompt_v*.prompt.txt` | The four rungs, each with the instruction that produced it. v2, v3 and v4 carry a **forbidden list** — every seed id, every action and tool name, and the display names of anything the prompt is supposed to describe — and each is asked to restate the judge specification for its own text. |
| `12_ladder.md` | Every rung side by side, a table of how each entity is referred to (with a **`uses`** column counting verbatim repeats — anything above 1 is the defect), the judge items per level, and the warnings. |
| `13_judge_prompt.txt` | The ninth call — the delivery judge, made at *eval* time, worth 0.4 of the reward. One section per level, since the items are restated at each rung. Graded over the whole rollout, not the final reply. |

## Things a reviewer will probably notice

Measured across the twelve, not claims from the docs:

- **The reference guarantee holds, and it is narrow.** Every one of the 31 references resolves to
  exactly one entity — the proofs are in each `04_references.result.txt`. But 29 of them are
  text-quoting modes (`message_by_text` 11, `user_authored_text` 10, `chat_containing_text` 8).
  The superlative modes — most-reacted, most-messages, member-count — are never chosen. So
  "resolve a reference" almost always means "find the message containing this exact phrase".
- **v3 stopped enumerating but did not stop sequencing.** No v3 prompt has line-start enumeration.
  But 6 of 12 still contain `; ` or
  ` then ` chaining the steps in order — which the V3 system prompt explicitly forbids
  ("no sentence that reads as 'and then'") and which nothing checks. Compare `11_ladder.md` for
  t7 or t11.
- **One task has no judge items at all.** t3's sequence has no value edge and no uncarried read,
  so `delivery` scores 1.0 for free and 0.4 of its reward is vacuous. It reads 1.00 in the
  delivery column at all three levels in `../samples/ladder_probe.md`.
- **Ids come back in through the content requirement.** t7 bans every id from the prompt text and
  then asks the agent to post "each chat id and name in prose". The forbidden list governs the
  instruction, not what the instruction asks for.
- **The judge hints still speak v1.** Hints name `c_001`, `m_009` and "step 4" even though the
  judge grades L3 rollouts where no step is identifiable. That is judge-side and invisible to the
  agent, but it means the hint describes a task the agent was never given.
- **Filler is expensive.** 24 of the additions across twelve tasks were rejected, nearly all for
  a sender who is not a member of the chat they are posting in.

## Files

| | |
| --- | --- |
| `PROMPTS.md` | Index of all eight LLM calls and the file holding each. |
| `run_review.py` | Drives the ten stages. Live (needs a key) or `--offline` (mechanical world, exact prompts). |
| `rebuild_from_samples.py` | Rebuilds every artifact from an authored task file. Needs nothing. |
| `01_sequences/` | Stage 1 for eleven indices, plus a shape table. |
| `02_authored/` | The twelve shipped tasks, taken apart. Real prose, real worlds. |
| `04_offline_exact_prompts/` | Four tasks with all seven prompts exact. Mechanical world, canned prose. |
| `03_live/` | Written by a live `run_review.py`. Absent until a run succeeds — and the only place genuine **correction rounds** appear. |
