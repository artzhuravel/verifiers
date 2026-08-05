# The ladder — t3

The same work asked for four ways, over one `(seed, expected)` pair. Nothing but the
specification's explicitness differs, so a score gap between two levels measures the gap
and not authoring noise.

The judge items say the same thing at every rung but are **restated** for each, because a
rung that removes step numbers and ids leaves an item written against the rung below
describing a task the agent was never given.

## How each thing is referred to

A description is meant to be used **once**, to introduce a thing; later mentions refer
back. `uses` counts how many times each rung pasted the description verbatim — anything
above 1 is the defect.

| symbol | entity | v1 says | the description | uses in v2/v3/v4 |
| --- | --- | --- | --- | --- |
| `$user_0` | Lina Park @lina | `u_lina` | "whoever wrote the message about We're planning to run" | 2/2 |
| `$user_1` | Ravi Patel @ravi | `u_ravi` | "whoever wrote the message about final schema for customer" | 2/2 |
| `$chat_0` | group 'ingest-pipeline' — members: You @you, Lina Park @lina, Ma | `c_001` | "the conversation where We're planning to run came up" | 2/2 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Create a new chat with name 'ingest-schedule-sync' that includes members u_lina and u_ravi (Lina Park @lina and Ravi Patel @ravi); you (u_me) are included automatically.
2. Send the message "Thanks — 02:00 works for me if ops can throttle noncritical retries during the window. @mae please post the hourly load so we can decide by EOD." to chat c_001 (the group 'ingest-pipeline').
3. In the chat you created in step 1, send the message "Quick sync: can you both weigh in on 02:00 vs 03:30 for the S3→warehouse ingest? We need to decide by EOD." and record the message id returned so subsequent steps can reference it.
4. Add the reaction '+1:' from you (u_me) to the message you created in step 3, using that message's id.
5. Add the reaction ':eyes:' from you (u_me) to the message you sent in step 2, using that message's id.
6. Reply in-thread to the message you created in step 3 with the text "Lina, can you confirm there are no conflicts at 02:00? Ravi, any downstream SLA concerns if we keep it then?".
```

### What the judge checks at L1

**(none)** — this sequence has no value edge and no uncarried read, so nothing needed judging. The `delivery` component scores 1.0 for free here, and 0.4 of this task's reward is vacuous.

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Please create a new chat named 'ingest-schedule-sync' that includes whoever wrote the message about We're planning to run and whoever wrote the message about final schema for customer; you will be included automatically. Then send the message "Thanks — 02:00 works for me if ops can throttle noncritical retries during the window. Please post the hourly load so we can decide by EOD." to the conversation where We're planning to run came up. In the chat you created, send the message "Quick sync: can you both weigh in on 02:00 vs 03:30 for the S3→warehouse ingest? We need to decide by EOD." and record the message id returned so subsequent steps can reference it. Add the reaction '+1:' from you to the message you created in that new chat, and add the reaction ':eyes:' from you to the message you sent to the conversation where We're planning to run came up. Finally, reply in-thread to the message you created in the new chat with the text "whoever wrote the message about We're planning to run, can you confirm there are no conflicts at 02:00? whoever wrote the message about final schema for customer, any downstream SLA concerns if we keep it then?" and report back in that new chat.
```

## L3 — the goal. No step individually identifiable.

```text
Create a new chat named ingest-schedule-sync that includes whoever wrote the message about We're planning to run and whoever wrote the message about final schema for customer, with me added automatically. In the conversation where We're planning to run came up, post this message: Thanks — 02:00 works for me if ops can throttle noncritical retries during the window. Please post the hourly load so we can decide by EOD. In the new ingest-schedule-sync chat, post: Quick sync: can you both weigh in on 02:00 vs 03:30 for the S3→warehouse ingest? We need to decide by EOD. React to the message you post in the new chat with +1: and react to the message you posted in the conversation where We're planning to run came up with :eyes:. Then reply in-thread to the message you created in the new chat with: whoever wrote the message about We're planning to run, can you confirm there are no conflicts at 02:00? whoever wrote the message about final schema for customer, any downstream SLA concerns if we keep it then? Report the results back into the new ingest-schedule-sync chat.
```

## Warnings recorded for this task

- stage 5 dropped: message n4: message 'n4' is from 'n1', who is not in 'c1'
- stage 5 dropped: message n7: message 'n7' is from 'u1', who is not in 'c2'
