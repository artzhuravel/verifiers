# L1 (explicit) vs L4 (conditional) — 3 rollouts per task

- **Agent** `openai/gpt-5-nano` · **judge** `openai/gpt-5-mini` · harness `null`
- 5 tasks x 3 rollouts = 15 rollouts per level
- Same tasks in both files (identical seed / expected / steps / golds); only `prompt` differs.

## Per level

| level | | mean | stdev | state_diff (.5) | tool_calls (.2) | open_ended (.3) | discovery reads | failed calls | unplanned writes |
|---|---|---|---|---|---|---|---|---|---|
| L1 | explicit | **0.881** | 0.122 | 0.495 | 0.200 | 0.186 | 22 | 2 | 0 |
| L4 | conditional | **0.785** | 0.226 | 0.403 | 0.200 | 0.182 | 61 | 0 | 1 |

## Per task (mean of 3 rollouts, with spread)

| idx | L1 mean | L1 rollouts | L4 mean | L4 rollouts | delta |
|---|---|---|---|---|---|
| 0 | 0.83 | [0.85, 0.7786, 0.85] | 0.95 | [0.85, 1.0, 1.0] | +0.12 |
| 1 | 1.00 | [1.0, 1.0, 1.0] | 0.75 | [0.6545, 0.9545, 0.6545] | -0.25 |
| 2 | 0.78 | [0.76, 0.82, 0.76] | 0.53 | [0.88, 0.38, 0.32] | -0.25 |
| 3 | 1.00 | [1.0, 1.0, 1.0] | 1.00 | [1.0, 1.0, 1.0] | +0.00 |
| 4 | 0.80 | [0.7, 0.7, 1.0] | 0.69 | [0.7, 0.6818, 0.7] | -0.11 |

## Paired result

- **Mean paired delta (L4 - L1): -0.096** (sd 0.162, se 0.072)
- Paired t = -1.33, df = 4 — **NOT statistically significant at p<0.05**
- Tasks worse at L4: **3/5** · better: 1/5

Pairing matters here: both levels contain the same five tasks, so differencing per
task removes task difficulty as a confound. But five tasks is five data points — the
direction is consistent while the mean is not separable from noise. The stronger
evidence is behavioural rather than in the reward: see the discovery-read and variance
columns above.
