# Every prompt in the system, and where to read it

Nine LLM calls exist in a task's life: eight while authoring it, one while scoring it. This
lists all nine, the file holding each, and the constant in the codebase it comes from.

`<t>` is a task directory — `t0` … `t11` under `02_authored/`, or `t1`, `t3`, `t9`, `t12` under
`04_offline_exact_prompts/`.

| # | stage | prompt file | system prompt in code | exact? |
| --- | --- | --- | --- | --- |
| — | 1 sequence | *no model call* | — | — |
| — | 2 shared context | not a prompt on its own; it is the first three blocks of all eight below. Read once in `<t>/02_shared_context.txt` | `render.shared_context` | exact |
| 1 | 3 world | `<t>/03_world.prompt.txt` | `authoring._ENTITIES_SYSTEM` | **exact** |
| 2 | 4 references | `<t>/04_references.prompt.txt` | `authoring._REFERENCES_SYSTEM` | exact in `04_offline_…`; later-world in `02_authored` |
| 3 | 5 populate | `<t>/05_populate.prompt.txt` | `authoring._POPULATE_SYSTEM` | exact in `04_offline_…`; later-world in `02_authored` |
| — | 6 replay | *no model call* | — | — |
| 4 | 7 content | `<t>/07_content.prompt.txt` | `authoring._CONTENT_SYSTEM` | **exact** |
| 5 | 8 v1 + judge spec | `<t>/08_prompt_v1.prompt.txt` | `prompts._V1_SYSTEM` | **exact** |
| 6 | 9 v2 | `<t>/09_prompt_v2.prompt.txt` | `prompts._V2_SYSTEM` | **exact** |
| 7 | 10 v3 | `<t>/10_prompt_v3.prompt.txt` | `prompts._V3_SYSTEM` | **exact** |
| 8 | 11 v4 | `<t>/11_prompt_v4.prompt.txt` | `prompts._V4_SYSTEM` | **exact** |
| 9 | delivery judge, at eval time | `<t>/12_judge_prompt.txt` | `verify._JUDGE_PROMPT` | exact but for the transcript, which needs a rollout. One section per level — the items are restated at each rung |

Every file carries the **system message** and the **user message** as the model received them,
then the reply. Nothing else in this folder is a prompt.

## Two things worth knowing before you read them

**Stages 4 and 5 are the only ones that cannot be reconstructed exactly** from a shipped task.
Both ran against the *core* world, before Stage 5 padded it, and only the padded world survives in
the record. So:

- `02_authored/<t>/04_…` and `05_…` are real in structure and instructions, with the later world
  substituted into the WORKSPACE block. Each file says so at the top.
- `04_offline_exact_prompts/<t>/04_…` and `05_…` are **exact**, because that run was driven
  end to end here. The world is mechanical (`tests/stub.py`) and the prose is canned, but every
  prompt is byte-for-byte what a model would receive. Read these for the two stages, and
  `02_authored/` for everything else.

**The twelve tasks in `02_authored/` predate the rewrite stages changing.** Their v2/v3 *replies*
were produced by the previous instruction — the one that asked for per-occurrence substitution and
left the judge items alone — while the instruction shown above each is the current one. That pairing
is deliberate: it is the before-and-after, and `L4_TARGET.md` reads it. None of them has a v4 reply,
since the rung did not exist when they were authored.

**Stage 7 does not always run.** `author_content` returns immediately when a sequence has no
`content` slot — every text param is a carry, whose value the agent supplies at rollout time.
That is the case for `t7`, whose `07_content.prompt.txt` says so instead of holding a prompt. Eight
of the eleven stages call a model; for t7 it is seven.

## Where the two prompt sets came from

```bash
# 02_authored — twelve real gpt-5-mini tasks, prompts reconstructed from the records
uv run --with-editable environments/my_env2 \
    python environments/my_env2/review/rebuild_from_samples.py

# 04_offline_exact_prompts — every prompt exact, mechanical world, no API key needed
uv run --with-editable environments/my_env2 \
    python environments/my_env2/review/run_review.py --offline --tasks 1,3,9,12

# 03_live — the real thing, prompts logged rather than rebuilt. Needs a working key.
uv run --with-editable environments/my_env2 \
    python environments/my_env2/review/run_review.py \
        --tasks 0,1,2,3,4,5,6,7,8,9,10,11 --model openai/gpt-5-mini
```

`03_live` is the authoritative set: twelve tasks authored by `openai/gpt-5-mini` through the
current pipeline, with every prompt **logged rather than rebuilt** — so all eight are exact, stages
4 and 5 included, and it is the only place genuine **correction rounds** appear (a rejected reply
handed back its own rejection message). No shipped record preserves those, and the offline run's
canned replies never fail a contract.

Read `02_authored/` only for the before-and-after: those twelve predate the rewrite-stage changes,
so their v2/v3 text is pre-fix output shown under the current instruction.

## The shape of an authoring prompt

All eight have the same skeleton. The shared context is always first, so every call decides
against the same account of what the environment means:

```
ENVIRONMENT                             ┐
ENTITY TYPES IN THIS TASK               │ shared_context — identical in all eight
ACTIONS THIS TASK USES                  ┘
<one to four blocks specific to the stage>
```

Stage by stage, the blocks after the shared context:

| stage | blocks it adds |
| --- | --- |
| 3 world | `PLAN THE AGENT WILL BE ASKED TO CARRY OUT` · `PLACEHOLDERS THAT MUST ALREADY EXIST` · `BIND EXACTLY THESE, ONE EACH, AND NOTHING ELSE` |
| 4 references | `WORKSPACE` · `ENTITIES TO DESCRIBE, AND THE MODES AVAILABLE FOR EACH` |
| 5 populate | `WORKSPACE SO FAR` (in *draft* vocabulary — `u1`, `c2`, `m3`) · `CONDITIONS` |
| 7 content | `WORKSPACE` · `PLAN` · `PLACEHOLDERS TO FILL` |
| 8 v1 | `WORKSPACE` · `PLAN (perform in this order)` · `ITEMS THAT NEED CHECKING` |
| 9 v2 | `WORKSPACE` · `PLAN THE TASK MUST STILL ENCODE` · `HOW TO REFER TO EACH THING INSTEAD OF NAMING IT` · `THESE STRINGS MUST NOT APPEAR IN YOUR TEXT` · `JUDGE ITEMS — REWRITE EACH ONE'S expected AND hint FOR YOUR TEXT` · `CURRENT TASK TEXT (rewrite this)` |
| 10 v3 | `WORKSPACE` · `PLAN YOUR TEXT MUST STILL LEAD TO (do not reproduce it)` · `KEEP REFERRING TO THINGS THIS WAY, AND NEVER BY NAME` · `THESE STRINGS MUST NOT APPEAR IN YOUR TEXT` · `JUDGE ITEMS — REWRITE EACH ONE'S expected AND hint FOR YOUR TEXT` · `CURRENT TASK TEXT (rewrite this)` |
| 11 v4 | the same five as v3, with a plan label that also says not to walk through it in order |

Stage 5 is the only call shown the world in draft vocabulary rather than real ids — that is what
lets it add a message to a conversation that already exists, instead of only inventing new rooms.
