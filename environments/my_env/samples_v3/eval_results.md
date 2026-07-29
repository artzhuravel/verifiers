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

---

## Worked example of a genuine failure — task idx 2 at L4/L5

The clearest failure in this batch, because it is **reproducible and level-dependent**:
the same task, needing the same single action, is scored full marks at L1–L3 and zero at
L4–L5, in both this run and the re-score.

| | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---|---|---|
| `state_diff` (weighted, max 0.50) | 0.50 | 0.50 | 0.50 | **0.00** | **0.00** |
| total | 0.82 | 0.82 | 0.88 | **0.32** | **0.38** |

The call sequence below is taken from `rescore/l5/traces.jsonl` — the original run's traces
were not preserved, but it reproduces the same `state_diff` 0.00 on the same task.

### What the task asked for

The plan's only graded state change is step 4 — one reaction:

```
4. [WRITE] chat_add_reaction  {"message_id": "m_035", "emoji": ":heart:"}
```

`m_035` lives in **c_006 (watercooler)**; it is Diego's reply reading *"That's the descale
alarm. It's been on for a month."* The L5 prompt wraps that reference in a condition:

> Then, **if the reply that said "That's the descale alarm. It's been on for a month."
> does not already have a :heart: reaction from you**, add a :heart: reaction to that
> reply, otherwise skip adding a reaction. […] Next, **mark as read the group where the
> message "Onboarding completion dropped to 41% this week." was posted.**

Nothing names the chat. The agent has to search the workspace for the quoted text.

### What the agent actually did

```
 1. x chat_send_message      {"chat_id":"c_missing", ...}      <- the intended invalid step
 2. + deepwiki_ask_question  {"repoName":"psf/requests", ...}
 3. + deepwiki_read_wiki_contents {"repoName":"psf/requests"}
 4. + chat_list_chats        {}
 5. + chat_read_messages     {"chat_id":"c_001","limit":50}
 6. + chat_read_messages     {"chat_id":"c_002","limit":50}
 7. + chat_read_messages     {"chat_id":"c_003","limit":50}
 8. + chat_read_messages     {"chat_id":"c_004","limit":80}
 9. + chat_add_reaction      {"message_id":"m_023","emoji":"❤️"}   <-- WRONG MESSAGE
10. + chat_list_chats        {}
11. + chat_mark_read         {"chat_id":"c_004"}
12-14. + deepwiki_ask_question x3
```

It listed the chats, then read **c_001 → c_004 and stopped**. The message it wanted is in
**c_006**, which it never opened. Having not found the quoted text, it reacted to `m_023`
in the last chat it had read — Noor's *"The drop starts at the workspace setup step."* in
**c_004**, which is the chat named by the *next* instruction (the mark-read target). The
two instructions were conflated, and the search was abandoned two chats early.

The target message exists, is uniquely identified by an exact quoted string, and the condition resolves the way the plan
intends (no `:heart:` from `u_me` on `m_035`). L1–L3 name the chat directly and the agent
gets it right every time.

### How that reached the score

This task's entire expected state change is one fact:

```
expected delta:  {('react', 'm_035', 'u_me')}
actual delta:    {('react', 'm_023', 'u_me')}
```

The intended fact is missing, so recall is 0 and **F1 = 0.00** — no partial credit is
possible, because there was only ever one thing to get right. Step 11's `chat_mark_read`
on `c_004` contributes nothing either way: all seven of that chat's messages were already
read by `u_me` in the seed.

```
total = 0.5 x 0.00 (state_diff) + 0.2 x 1.00 (tool_calls) + 0.3 x 0.40 (open_ended) = 0.32
```

(That is the re-score rollout shown above. The original run's L5 total was 0.38 — the same
`state_diff` 0.00, differing only in the judge component, which is resampled every run.)

---

### The two prompts side by side — L2 (passed) vs L4 (failed)

Same task, same required action. L2 scored **0.82**, L4 scored **0.32**. Only the prompt
differs, and almost all of that difference is one sentence:

| | L2 — passed | L4 — failed |
|---|---|---|
| the reaction clause | "Then add a :heart: reaction to the message that says *'That's the descale alarm. It's been on for a month.'* **in the casual channel where the espresso conversation appears**." | "Then, **if** the reply that said *'That's the descale alarm. It's been on for a month.'* **does not already have a :heart: reaction from you**, add a :heart: reaction to that reply; **otherwise skip adding a reaction**." |
| names a chat? | **yes** — "the casual channel where the espresso conversation appears" points at c_006 | **no** — the chat is never referred to at all |
| conditional? | no | yes |

**Two things changed at once.** L4 was
meant to *add* a condition and it also **dropped
the locator**: L2 tells the agent which channel to look in, L4 does not. The agent that
failed never opened c_006 — consistent with having no pointer to it, not with being
confused by the `if`.

So this pair is weaker evidence for "conditionals are hard" than it first appears, and
better evidence for something more useful: **a rewrite can quietly delete the information
that made a reference resolvable, and nothing in the pipeline currently notices** (the
missing solvability check, HANDOFF §8.1). Separating the two effects would need an L4
variant that keeps the locator and adds only the condition.

#### L2 — descriptive (1559 chars) — total 0.82

```text
Please do the following things in order and then tell me what you found in your reply. First, try to send the message text "shipping it" to the chat identified as c_missing and tell me whether that send succeeded or failed. Next, read the repository layout at the root of the GitHub repo 'psf/requests' and answer this exact question: "List the top-level files and directories in the root of the GitHub repo 'psf/requests' (names only)." Let me know what you find. After that, read the README content for the GitHub repo 'psf/requests' and answer this exact question: "What is the exact one-line project description shown at the top of README.md in the GitHub repo 'psf/requests' (the first sentence or tagline)?" Let me know what you find. Then add a :heart: reaction to the message that says "That's the descale alarm. It's been on for a month." in the casual channel where the espresso conversation appears. After adding the reaction, get a list of all chats visible to you and return that list. Then mark as read the group where the message "Onboarding completion dropped to 41% this week." was posted. Finally, ask the following three repository questions and, for each one, tell me the answer in your reply: "What license does the repository 'facebook/react' use?" "What is the primary programming language of the GitHub repo 'django/django'?" "Which organization owns or maintains the 'tensorflow/tensorflow' GitHub repository (who is listed as the repo owner)?" For each of the repository lookups above, please let me know what you find in your reply.
```

#### L4 — conditional (1595 chars) — total 0.32

```text
Please do these things in order and then tell me what you found in your reply. First, try to send the message text "shipping it" to the chat identified as c_missing and tell me whether that send succeeded or failed. Next, inspect the top-level layout at the root of the GitHub repo 'psf/requests' and answer this exact question: "List the top-level files and directories in the root of the GitHub repo 'psf/requests' (names only)." Let me know what you find. After that, open the README for the same repo and answer this exact question: "What is the exact one-line project description shown at the top of README.md in the GitHub repo 'psf/requests' (the first sentence or tagline)?" Let me know what you find. Then, if the reply that said "That's the descale alarm. It's been on for a month." does not already have a :heart: reaction from you, add a :heart: reaction to that reply; otherwise skip adding a reaction. After you've added the reaction if applicable (or skipped it because you already reacted), get a list of all chats visible to you and return that list. Next, mark as read the group where the message "Onboarding completion dropped to 41% this week." was posted. Finally, ask and answer these repository questions and tell me what you find for each: "What license does the repository 'facebook/react' use?" "What is the primary programming language of the GitHub repo 'django/django'?" "Which organization owns or maintains the 'tensorflow/tensorflow' GitHub repository (who is listed as the repo owner)?" For each of the repository lookups above, please let me know what you find.
```
