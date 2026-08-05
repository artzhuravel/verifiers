# The ladder — t2

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
| `$user_0` | Alice Rivera @alice | `u_alice` | "whoever wrote the message about feature freeze Aug 10" | 1/1 |
| `$user_1` | Ben Turner @ben | `u_ben` | "whoever wrote the message about migration to next week" | 1/1 |
| `$user_2` | Cara Malik @cara | `u_cara` | "whoever wrote the message about could we shift beta" | 1/1 |
| `$user_3` | Diego Ramos @diego | `u_diego` | "whoever wrote the message about clash with marketing deadlines" | 1/1 |
| `$chat_0` | dm (unnamed dm) — members: Sam Park @you, Ben Turner @ben | `c_002` | "the conversation where migration to next week came up" | 1/1 |
| `$message_0` | in launch-planning from Diego Ramos, replying to m_001, unread b | `m_005` | "the latest thing @diego posted" | 0/1 |
| `$message_1` | in c_002 from Ben Turner, replying to m_006, unread by you: "Als | `m_008` | "the reply to the message about migration to next week" | 1/1 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Call list_chats to list the chats the acting user (u_me) is a member of.
2. Create a new chat with member_ids [u_alice, u_ben] and name "Vendor & DB Coordination".
3. Create a new chat with member_ids [u_cara, u_diego] and name "Launch Contingency".
4. Send a message to chat c_002 with a text body that CARRIES (includes) the full result returned by step 1 (the list_chats array); the list_chats result must appear in the message text you send to c_002.
5. Reply to message m_005 in chat c_001 with a reply text that CARRIES (includes) the full result returned by step 1 (the list_chats array); the list_chats result must appear in the reply text you post to m_005.
6. Reply to message m_008 in chat c_002 with a reply text that CARRIES (includes) the full result returned by step 1 (the list_chats array); the list_chats result must appear in the reply text you post to m_008.
After completing the actions above, include in your reply the returned objects for the two created chats from steps 2 and 3 (so I can see their ids and member lists) and the created message objects for steps 4–6.
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: The message sent to chat c_002 contains a listing of the three chats the acting user belongs to: c_001 (a group named "launch-planning" with members u_me, u_alice, u_cara, u_diego), c_002 (a DM named "c_002" with members u_me and u_ben), and c_003 (a group named "reading-club" with members u_me, u_alice, u_evan).
    - where to look: Look in the text of the message you posted in step 4 (the send_message to chat c_002).
- **carry:c1a1:text**
    - a correct answer says: The reply posted to m_005 states the three chats the acting user belongs to: c_001 (group "launch-planning" with members u_me, u_alice, u_cara, u_diego), c_002 (DM "c_002" with members u_me and u_ben), and c_003 (group "reading-club" with members u_me, u_alice, u_evan).
    - where to look: Look in the text of the reply you posted to message m_005 (step 5).
- **carry:c0a2:text**
    - a correct answer says: The reply posted to m_008 states the three chats the acting user belongs to: c_001 (group "launch-planning" with members u_me, u_alice, u_cara, u_diego), c_002 (DM "c_002" with members u_me and u_ben), and c_003 (group "reading-club" with members u_me, u_alice, u_evan).
    - where to look: Look in the text of the reply you posted to message m_008 (step 6).

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Please list the chats the acting user is a member of, then create a new chat including whoever wrote the message about feature freeze Aug 10 and whoever wrote the message about migration to next week and name that chat "Vendor & DB Coordination", then create another new chat including whoever wrote the message about could we shift beta and whoever wrote the message about clash with marketing deadlines and name that chat "Launch Contingency", then send a message to the conversation where migration to next week came up whose text includes the full result returned by the first action (the array of chats returned by the initial listing), then reply to the latest thing the person who wrote the message about clash with marketing deadlines posted with a reply that includes the full result returned by the first action (the array of chats), and then reply to the reply to the message about migration to next week with a reply that includes the full result returned by the first action (the array of chats); after completing these actions, include in your reply the returned objects for the two created chats and the created message objects for the three messages you sent.
```

## L3 — the goal. No step individually identifiable.

```text
Gather a current listing of the chats I’m a member of and use that listing as the context to create focused coordination spaces and to seed context into the existing threads: create a new chat named Vendor & DB Coordination that includes whoever wrote the message about feature freeze Aug 10 and whoever wrote the message about migration to next week, and create a new chat named Launch Contingency that includes whoever wrote the message about could we shift beta and whoever wrote the message about clash with marketing deadlines. Post a new message into the conversation where migration to next week came up whose text contains the full array returned by the initial chat listing, reply in-thread to the latest thing @diego posted with a message whose text contains that same array, and reply in-thread to the reply to the message about migration to next week with a message whose text contains that same array.
```

## Warnings recorded for this task

- stage 5 dropped: message n6: message 'n6' is from 'n1', who is not in 'c2'
