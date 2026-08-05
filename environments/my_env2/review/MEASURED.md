# Did the changes work?

Twelve tasks, the same twelve indices, authored twice: `../samples/tasks.jsonl` before the rewrite
stages changed and `03_live/tasks.jsonl` after, both by `openai/gpt-5-mini`. Everything below is
counted, not asserted — reproduce with:

```bash
uv run --with-editable environments/my_env2 python environments/my_env2/review/measure_fixes.py
uv run --with-editable environments/my_env2 python environments/my_env2/review/per_level.py \
    environments/my_env2/samples/tasks.jsonl environments/my_env2/review/03_live/tasks.jsonl
uv run --with-editable environments/my_env2 python environments/my_env2/review/show_leaks.py
```

The after run: **12 authored, 0 dropped, 103 model calls** (8 per task plus 7 correction rounds).

## 1. Judge drift — fixed

An item authored against v1 says *"Look in the reply message posted to m_002 (the message created in
step 4)"*. Served unchanged at L3, it points a grader at a task with no `m_002` and no steps.

| | before | after |
|---|---:|---:|
| judge items across the de-scaffolded rungs | 56 | 84 |
| **whose `hint` still names an id or tool, or which cite a step number** | **54** | **2** |
| id/tool-name leaks | 72 | 2 |
| step-number references | 44 | 0 |

The two survivors are the same item at v2 and v3 in t9, whose hint says "the reported `list_chats`
output" — a tool name, which the prompt never mentions. Harmless to the agent, which never sees the
judge, but it is drift and it is recorded as a warning.

It is a real rewrite, not a no-op: **0 of 28 items** have a byte-identical hint at L1 and L4.

```
L1  Look in the reply message posted to m_002 (the message created in step 4).
L2  Look in the reply message you posted to the message about doc-topic list for
    acme/monitoring (the message created when you carried the combined information).
L4  Check the reply you posted in the thread that asked for the doc-topic list for
    acme/monitoring — the message you created that combines the chat list and the
    DeepWiki topic titles.
```

`requirement` is identical at every rung throughout — *"the text of step 4 must carry what step 2
and step 1 returned"*. It is derived, states the obligation in plan terms, and is never authored,
along with `id` and `delivered_in`.

## 2. Repetition — halved, not fixed

Per rung, how many of the 41 reference uses were the description stated once, pasted more than
once, or never stated at all:

| rung | | refs | used 1× | **>1×** | 0× | sequencing |
|---|---|---:|---:|---:|---:|---:|
| L2 | before | 41 | 19 | **21** | 1 | 42 |
| L2 | after | 41 | 30 | **11** | 0 | 32 |
| L3 | before | 41 | 22 | **19** | 0 | 15 |
| L3 | after | 41 | 32 | **9** | 0 | 17 |
| L4 | after | 41 | 6 | **4** | 31 | 18 |

L2 51% → 27%, L3 46% → 22%, worst case 5× → 4×. The instruction helps materially, and roughly a
quarter of references are still pasted twice.

**The 31 zero-uses are all L4 and all intended.** L4 may render a description in natural English
instead of quoting it, so `require_verbatim` is off there and on at L2/L3 — where the count is now
**zero**, down from 1. No rung that was told to use a description dropped one.

## 3. Sequencing — not fixed

L3 was 15 connectives (`; `, ` then `) over 12 tasks; it is now 17. L4 is 18. Normalised per task
that is 1.25 → 1.42, i.e. slightly worse.

The L4 instruction asks for folding in some detail — it names the failure ("every action gets its
own clause, in the plan's order"), gives a worked before/after, and bans hand-off vocabulary. The
hand-off vocabulary partly went: counting "retain", "for later use", "kept for later" and
"returned", L3 fell from 18 occurrences to 12, and L4 sits at 7. So the *narration* of the data flow
thinned, but the clause-per-action ordering it narrated survived, joined by semicolons instead of
"then".

This is the one change of four that did not land. Prohibiting a connective was the wrong lever —
the model complies locally and reorders nothing. What would probably work is showing a folded pair
in the prompt as the target rather than describing one, or computing the fold candidates the way
`merge_candidates` did in the previous pipeline and naming which steps to combine. It is recorded
as a warning at L3 and L4 now, so at least it is visible.

## 4. Self-invalidating references — detected, still present

`t1` still uses `chat_only_with_unread` — "the one conversation you still have not caught up on" —
in a task whose third step marks that conversation read. `stale_references` catches it and the
rewrite stages are told, which is exactly the case the "use it early, once, then refer back" rule was
written for — and it worked: the phrase went from **4 uses at both v2 and v3** to **1 at each of v2,
v3 and v4**. So the description is now stated before the step that falsifies it and never after.

Detection is still not prevention:
Stage 4 picks the mode before `expected` exists, so the honest fix is to re-run mode selection after
replay and reject a mode the task destroys. Not built.

## A correction to the checker

The first version of `_judge_leaks` applied the forbidden-list test to `expected` as well as `hint`,
and reported 5 leaks. Three were t8 items whose expected answers read *"includes Cara's handle
@cara"* — which is exactly right, because delivering that handle **is** the task. `expected` is the
answer key and must be allowed to state the answer; `hint` says where to look and must not hand over
the resolution step. The check now tests the forbidden list against `hint` only, and step numbers
against both. Without that split the tool would have reported the author failing where it had
succeeded.

## Where to read the artifacts

| | |
| --- | --- |
| `03_live/t<n>/` | The after set. Eight prompt files each, logged not rebuilt, plus `12_ladder.md` with all four rungs and the per-level judge items. |
| `02_authored/t<n>/` | The before set, with the current instruction shown above each historical reply. |
| `L4_TARGET.md` | Why the fourth rung exists, worked through on t1. |
