# A first measurement

Twelve tasks authored by `openai/gpt-5-mini`, solved by `openai/gpt-5-nano`, one rollout each at
every level. Same seed, same expected state, same judge items across the three columns — only the
wording differs, which is what makes them comparable.

The tasks themselves are in `tasks.jsonl` beside this file. Reproduce with:

```bash
uv run eval @ environments/my_env2/eval.toml \
  --env.taskset.dataset environments/my_env2/samples/tasks.jsonl \
  --env.taskset.level <1|2|3>
```

| idx | L1 | sd | del | L2 | sd | del | L3 | sd | del |
|----:|---:|---:|----:|---:|---:|----:|---:|---:|----:|
| 0 | 0.450 | 0.75 | 0.00 | 0.150 | 0.25 | 0.00 | 0.300 | 0.50 | 0.00 |
| 1 | 0.629 | 0.71 | 0.50 | 0.309 | 0.18 | 0.50 | 0.000 | 0.00 | 0.00 |
| 2 | 1.000 | 1.00 | 1.00 | 0.747 | 0.80 | 0.67 | 1.000 | 1.00 | 1.00 |
| 3 | 1.000 | 1.00 | 1.00 | 0.954 | 0.92 | 1.00 | 1.000 | 1.00 | 1.00 |
| 4 | 1.000 | 1.00 | 1.00 | 0.000 | 0.00 | 0.00 | 0.769 | 0.62 | 1.00 |
| 5 | 0.600 | 0.67 | 0.50 | 1.000 | 1.00 | 1.00 | 0.514 | 0.86 | 0.00 |
| 6 | 0.343 | 0.57 | 0.00 | 0.000 | 0.00 | 0.00 | 0.000 | 0.00 | 0.00 |
| 7 | 1.000 | 1.00 | 1.00 | 1.000 | 1.00 | 1.00 | 1.000 | 1.00 | 1.00 |
| 8 | 0.900 | 1.00 | 0.75 | 0.700 | 0.67 | 0.75 | 1.000 | 1.00 | 1.00 |
| 9 | 0.500 | 0.50 | 0.50 | 0.800 | 1.00 | 0.50 | 0.700 | 1.00 | 0.25 |
| 10 | 0.733 | 0.89 | 0.50 | 0.636 | 0.73 | 0.50 | 0.500 | 0.50 | 0.50 |
| 11 | 0.400 | 0.67 | 0.00 | 1.000 | 1.00 | 1.00 | 0.450 | 0.75 | 0.00 |

|  | total | `state_diff` | `delivery` |
|---|---:|---:|---:|
| **L1** explicit, ids named | 0.713 | 0.813 | 0.562 |
| **L2** prose, references described | 0.608 | 0.629 | 0.576 |
| **L3** goal-level | 0.603 | 0.685 | 0.479 |

## What this says

**The tasks are gradeable and the two components are not redundant.** Scores spread across the
whole range, both components move, and they move independently — idx 5 at L3 does the state work
and delivers nothing; idx 4 at L3 gets most of the state wrong and delivers everything.

**Removing the ids costs about a tenth of the score. The two de-scaffolded levels are level with
each other.** L1 → L2 is the drop you would expect from making the agent resolve references itself.
L2 → L3 is 0.005, which is nothing.

**None of these three differences is separable at this sample size, and the temptation to read them
is worth resisting.** An earlier run over eight of these tasks gave 0.735 / 0.311 / 0.508 — the
middle rung hardest by a wide margin, with a plausible story attached about descriptive-but-still-
enumerated prose being the worst of both. It did not replicate: four more tasks and a re-author put
L2 at 0.608. Twelve tasks at one rollout each cannot separate conditions this close, and the
earlier spread was sampling noise.

**What this does establish** is that the pipeline produces tasks that run, score and discriminate.
Separating the levels needs more tasks and several rollouts each — and the shape metadata in every
record exists so that when that data arrives the question can be asked of realized structure (chain
length, cross-thread edges, fan-in, how many references are superlatives) rather than of the level
label alone.
