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
| `$user_0` | Lena Cho @lena | `u_lena` | "whoever wrote the message about Where are we sourcing" | 1/1/0 |
| `$user_1` | Rafael Gomez @rafael | `u_rafael` | "whoever wrote the message about Vendor quote came back" | 1/1/0 |
| `$chat_0` | group 'Product Research' — members: Avery Chen @you, Lena Cho @l | `c_001` | "the one conversation you still have not caught up on" | 1/1/0 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Call create_chat with member_ids = [u_lena, u_rafael] and name = 'Usability Recruiting'; keep the id returned by this call for use in step 3.
2. Call send_message to chat_id = c_001 with text "Quick decision needed: should we lock to 12 sessions if Finance approves reallocating ~$250 for incentives, or cut to 8? I recommend locking to 12—any objections?" and keep the id returned by this call for use in step 5.
3. Call send_message to the chat created in step 1 (use the id returned by step 1) with text "Finance will review the $250 reallocation tomorrow. Rafael, please confirm when they respond; Lena, can you confirm panel/paying options so we can commit to 12 if approved?" and keep the id returned by this call for use in steps 4 and 6.
4. Call add_reaction with message_id = the id returned by step 3 and emoji = ':+1:'.
5. Call add_reaction with message_id = the id returned by step 2 and emoji = ':+1:'.
6. Call reply_to with message_id = the id returned by step 3 and text "Thanks — I'll hold off booking until Finance and Lena confirm.".
```

### What the judge checks at L1

**(none)** — this sequence has no value edge and no uncarried read, so nothing needed judging. The `delivery` component scores 1.0 for free here, and 0.4 of this task's reward is vacuous.

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Create a new chat that includes you and whoever wrote the message about Vendor quote came back and whoever wrote the message about Where are we sourcing, name the chat 'Usability Recruiting', and retain its id for later. Then send a message to the one conversation you still have not caught up on that says "Quick decision needed: should we lock to 12 sessions if Finance approves reallocating ~$250 for incentives, or cut to 8? I recommend locking to 12—any objections?" and keep its id for later. Next send a message to the chat you created that says "Finance will review the $250 reallocation tomorrow. The first person you added, please confirm when they respond; the second person you added, can you confirm panel/paying options so we can commit to 12 if approved?" and keep that id for the next actions. React with :+1: (from you) to the message you just sent to the new chat, and also react with :+1: (from you) to the message you sent in the conversation you had not yet caught up on; finally, reply in thread to the message you sent in the new chat with "Thanks — I'll hold off booking until Finance and the second person you added confirm.", retaining the reply's id if needed.
```

### What the judge checks at L2

**(none)** — this sequence has no value edge and no uncarried read, so nothing needed judging. The `delivery` component scores 1.0 for free here, and 0.4 of this task's reward is vacuous.

## L3 — the goal. No step individually identifiable.

```text
Create a new chat that includes you plus whoever wrote the message about Vendor quote came back and whoever wrote the message about Where are we sourcing; name that chat 'Usability Recruiting' and retain its id for later. Post this to the one conversation you still have not caught up on: Quick decision needed: should we lock to 12 sessions if Finance approves reallocating ~$250 for incentives, or cut to 8? I recommend locking to 12—any objections? Save that message id. In the new chat, say that Finance will review the $250 reallocation tomorrow, ask the first person you added to confirm when Finance responds, and ask the second person you added to confirm panel/paying options so we can commit to 12 if approved; keep that message id. React with :+1: (from you) to the message you posted in the conversation you were behind on and to the message you posted in the new chat. Reply in-thread to the message you sent in the new chat with: Thanks — I'll hold off booking until Finance and the second person you added confirm, and retain that reply's id if needed.
```

### What the judge checks at L3

**(none)** — this sequence has no value edge and no uncarried read, so nothing needed judging. The `delivery` component scores 1.0 for free here, and 0.4 of this task's reward is vacuous.

## L4 — folded. Actions that existed only to feed each other become one request, no content is dictated word for word, and no clause narrates a hand-off.

```text
Make a new group chat named "Usability Recruiting" that includes you plus the person who posted the vendor-quote message and the person who asked where we're sourcing participants. In the conversation you still haven't caught up on, post a short, urgent decision request asking whether we should lock to 12 sessions if Finance approves reallocating ~$250 for participant incentives, or cut to 8; state your recommendation to lock to 12 and ask for any objections. In the new "Usability Recruiting" chat, say that Finance will review the $250 reallocation tomorrow, ask the vendor-quote author to confirm when Finance responds, and ask the sourcing author to confirm panel/payment options so we can commit to 12 if approved. Add a thumbs-up reaction (from you) to the message you just posted in the conversation you were behind on and to the message you posted in the new chat. Finally, post an in-thread reply to your message in the new chat saying you'll hold off booking until Finance and the sourcing author confirm.
```

### What the judge checks at L4

**(none)** — this sequence has no value edge and no uncarried read, so nothing needed judging. The `delivery` component scores 1.0 for free here, and 0.4 of this task's reward is vacuous.

## Warnings recorded for this task

- v3: 2 sequencing connective(s) — reads as a list in prose clothing
- v4: 1 sequencing connective(s) — reads as a list in prose clothing
