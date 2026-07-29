# Re-score after the adapter.signature change (in/replyto facts)

Agent gpt-5-nano - judge gpt-5-mini - harness null - 1 rollout/task - samples_v3

| level | | mean | state_diff | tool_calls | open_ended | disc reads | failed calls |
|---|---|---|---|---|---|---|---|
| L1 | explicit | **0.877** | 0.982 | 1.000 | 0.620 | 7 | 2 |
| L2 | descriptive | **0.900** | 0.908 | 1.000 | 0.820 | 20 | 0 |
| L3 | relational | **0.951** | 0.973 | 1.000 | 0.880 | 13 | 0 |
| L4 | conditional | **0.811** | 0.874 | 1.000 | 0.580 | 23 | 0 |
| L5 | noisy | **0.756** | 0.643 | 1.000 | 0.780 | 18 | 0 |

## vs the pre-fix run (same tasks, 1 rollout each)

| level | before | after | delta |
|---|---|---|---|
| L1 explicit | 0.934 | **0.877** | -0.057 |
| L2 descriptive | 0.865 | **0.900** | +0.035 |
| L3 relational | 0.937 | **0.951** | +0.014 |
| L4 conditional | 0.735 | **0.811** | +0.076 |
| L5 noisy | 0.777 | **0.756** | -0.021 |

## Per task (total reward)

| idx | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---|---|---|
| 0 | 0.80 | 0.67 | 0.98 | 0.85 | 0.77 |
| 1 | 1.00 | 0.95 | 0.95 | 0.95 | 0.95 |
| 2 | 0.88 | 0.88 | 0.82 | 0.82 | 0.32 |
| 3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 4 | 0.70 | 1.00 | 1.00 | 0.43 | 0.73 |

## state_diff only (the component the signature change affects)

| idx | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---|---|---|
| 0 | 0.91 | 0.63 | 0.96 | 1.00 | 0.85 |
| 1 | 1.00 | 0.91 | 0.91 | 0.91 | 0.91 |
| 2 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| 3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 4 | 1.00 | 1.00 | 1.00 | 0.46 | 0.46 |

rollouts with errors / abnormal stop: none
overall mean 0.859, sd 0.180

## Notable rollouts (diagnosed from the transcripts)

- **L5 idx2 — state_diff 0.00.** Expected delta is a *single* fact,
  `('react','m_035','u_me')`. The agent reacted to `m_023` instead, so F1 = 0. This is the
  degenerate-task hazard (HANDOFF §8.4) firing: on a 1-fact task the 0.5-weighted
  component is all-or-nothing.
- **L4/L5 idx4 — state_diff 0.46.** The agent produced all 3 expected facts, then also
  called `chat_mark_read(c_003)`, which is *not* in the plan (the plan has
  `chat_read_messages(c_003)`). c_003 holds 7 messages, so that one incidental write added
  7 unexpected `read` facts and dropped precision to ~0.3. A single plausible side-effect
  outweighed the entire intended task.
- **L1 idx0 — state_diff 0.91.** The agent passed `member_ids:["maya"]` (the *handle*)
  where `u_maya` (the *id*) was required. `create_chat` does not validate members
  (`enforced: false`), so it silently created a chat containing a nonexistent user.
- **idx1 / idx4 open_ended.** Their plans sample `deepwiki_read_wiki_contents`, but the
  authored gold asks for repo *metadata* (language / license / maintainers) that the wiki
  page does not state. The agent correctly reported "not stated" and the judge correctly
  scored 0 — the question is unanswerable with the tool the plan specifies.
