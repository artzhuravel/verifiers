# Ambiguity ladder — eval results

- **Agent** `openai/gpt-5-nano` · **judge** `openai/gpt-5-mini` · harness `null` · 1 rollout/task
- **Dataset** `samples_v2/authored_tasks_l1..l3.jsonl` — 5 tasks, 4–8 actions each
- Levels are paired: identical seed / expected state / steps / golds; only `prompt` differs.

## Per level

| level | mean reward | state_diff (max .5) | tool_calls (max .2) | open_ended (max .3) | unplanned writes | failed calls | errors |
|---|---|---|---|---|---|---|---|
| L1 | **0.827** | 0.387 | 0.200 | 0.240 | 0 | 5 | 0 |
| L2 | **0.970** | 0.500 | 0.200 | 0.270 | 0 | 0 | 0 |
| L3 | **0.945** | 0.475 | 0.200 | 0.270 | 2 | 0 | 0 |

## Per task (total reward)

| idx | L1 | L2 | L3 | L1→L3 |
|---|---|---|---|---|
| 0 | 1.00 | 1.00 | 0.94 | -0.06 |
| 1 | 0.78 | 0.85 | 0.78 | -0.01 |
| 2 | 0.85 | 1.00 | 1.00 | +0.15 |
| 3 | 1.00 | 1.00 | 1.00 | +0.00 |
| 4 | 0.50 | 1.00 | 1.00 | +0.50 |

## Finding: the ladder is inverted

L1 — the rung meant to be the trivially-solvable floor — scores **worst**, and the
whole gap is `state_diff`. The cause is visible in idx 4, which scores 0.50 at L1 and
1.00 at L2 and L3.

L1 names the tool but not the entity: *"Call chat_send_message ... with the DM that
contains you and Alex @alex.chen"*. Told exactly which function to invoke, the agent
invoked it immediately and guessed the argument:

```
chat_send_message {"chat_id": "dm-alex-chen"}   -> no such chat
chat_send_message {"chat_id": "alex.chen"}      -> no such chat
chat_send_message {"chat_id": "dm_alex_chen"}   -> no such chat
chat_send_message {"chat_id": "DM_ALEX_CHEN"}   -> no such chat
```

It never called `chat_list_chats`, so the message was never sent and `state_diff` was 0.
At L2 the same task is phrased descriptively, the agent has no tool name to anchor on,
and it discovers first — `chat_list_chats` -> `chat_read_messages` -> send to `c_005`.

So naming a tool suppresses discovery. A prompt that is specific about the *tool* but
vague about the *entity* is harder than one that is vague about both, because it invites
the agent to act before looking. That is a property of the L1 phrasing, not a difficulty
signal — L1 is not currently a usable easy floor.

## Caveats

- **n=5, 1 rollout each.** Differences of less than roughly 0.1 mean reward are not
  distinguishable from noise at this sample size. The L1 gap is driven by a single task
  (idx 4), so treat the size of it as indicative only — the *mechanism* is confirmed.
- No solvability check runs on L2/L3, so a broken rewrite and a genuinely hard one
  score identically. A drop is evidence of difficulty *or* of damage.
- `open_ended` returns 1.0 when a task has no open items, which inflates it uniformly
  across levels (same tasks, so it does not bias the comparison).
- `unplanned writes` counts only state-changing calls that **succeeded** beyond the plan
  (intended invalid steps excluded) — it tests whether dropping the "perform only these
  operations" trailer made the agent freelance. `failed calls` counts calls that returned
  an error other than the intended invalid steps, which is where L1's flailing shows up.
