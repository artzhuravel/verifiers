# Ambiguity ladder — eval results

- **Agent** `openai/gpt-5-nano` · **judge** `openai/gpt-5-mini` · harness `null` · 1 rollout/task
- **Dataset** `samples_v3/authored_tasks_l1..l5.jsonl` — 5 tasks
- Levels are paired: identical seed / expected state / steps / golds; only `prompt` differs.

## Per level

| level | | mean reward | state_diff (.5) | tool_calls (.2) | open_ended (.3) | discovery reads | failed calls | unplanned writes |
|---|---|---|---|---|---|---|---|---|
| L1 | explicit | **0.934** | 0.500 | 0.200 | 0.234 | 7 | 0 | 0 |
| L2 | descriptive | **0.865** | 0.491 | 0.200 | 0.174 | 23 | 0 | 0 |
| L3 | relational | **0.937** | 0.491 | 0.200 | 0.246 | 15 | 0 | 0 |
| L4 | conditional | **0.735** | 0.301 | 0.200 | 0.234 | 19 | 0 | 1 |
| L5 | noisy | **0.777** | 0.391 | 0.200 | 0.186 | 19 | 0 | 0 |

## Per task (total reward)

| idx | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---|---|---|
| 0 | 0.85 | 0.85 | 0.85 | 0.72 | 0.85 |
| 1 | 1.00 | 0.95 | 0.95 | 0.95 | 0.95 |
| 2 | 0.82 | 0.82 | 0.88 | 0.32 | 0.38 |
| 3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 4 | 1.00 | 0.70 | 1.00 | 0.68 | 0.70 |

## Reading this

- **n=5, 1 rollout each.** Gaps under ~0.1 mean reward are not separable from noise.
- `discovery reads` counts read-only chat calls made before the first successful write —
  a proxy for whether a rung actually forces the agent to inspect the app.
- `failed calls` counts errored calls other than the intended invalid steps; it is where
  guessing at ids shows up.
- `unplanned writes` counts successful state-changing calls beyond the plan.
- No solvability check runs on L2+, so a drop is evidence of difficulty *or* of damage.
