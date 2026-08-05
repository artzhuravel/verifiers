# The ladder — t7

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
| `$chat_0` | group 'Launch Planning' — members: Ari Novak @you, Samir Patel @ | `c_001` | "the Launch Planning channel" | 1/4/2 |
| `$user_0` | Maria Gomez @maria | `u_maria` | "whoever wrote the message about 02:00 I'll be on" | 1/1/0 |
| `$chat_1` | group 'Ops Room' — members: Ari Novak @you, Maria Gomez @maria,  | `c_003` | "the Ops Room channel" | 1/3/1 |
| `$message_0` | in Ops Room from Tom Wright, unread by you: 'Alert: the canary s | `m_007` | "the message about canary shows increased latencies" | 1/1/0 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Call list_chats and return the list of chats the acting user (u_me) is a member of; record that result for use in later steps.  
2. Read the most recent messages in chat c_001 (Launch Planning) and include those message views in your final reply so I can see what was returned.  
3. Create a new chat that includes member u_maria (Maria Gomez) in addition to the acting user.  
4. Send a message to chat c_001 (Launch Planning) whose text includes (carries) the list of chats returned by step 1.  
5. Send a message to chat c_003 (Ops Room) whose text includes (carries) the list of chats returned by step 1.  
6. Reply to message m_007 in Ops Room with a threaded reply whose text includes (carries) the list of chats returned by step 1.
```

### What the judge checks at L1

- **report:c1a0**
    - a correct answer says: A concise summary stating the recent messages read from the Launch Planning chat: m_001 from Samir asking to pick the time window (22:00 or 02:00); m_002 from Leah saying 02:00 is safer for international traffic and to flag the CS team; m_003 from Maria asking someone to draft a clear rollback plan with triggers; and m_006 from Samir noting external stakeholders asked for a one-pager.
    - where to look: Look in the agent's final reply where it summarizes or lists the messages returned by reading chat c_001 (Launch Planning).
- **carry:c0a1:text**
    - a correct answer says: The message posted to c_001 (Launch Planning) includes the full list of chats returned by step 1, naming each chat id and name: c_001 "Launch Planning" (group), c_002 (dm), c_003 "Ops Room" (group), and c_004 "Watercooler" (group).
    - where to look: Find this in the text of the message the agent sent to chat c_001 in step 4.
- **carry:c1a1:text**
    - a correct answer says: The message posted to c_003 (Ops Room) includes the full list of chats returned by step 1, naming each chat id and name: c_001 "Launch Planning" (group), c_002 (dm), c_003 "Ops Room" (group), and c_004 "Watercooler" (group).
    - where to look: Find this in the text of the message the agent sent to chat c_003 in step 5.
- **carry:c0a2:text**
    - a correct answer says: The threaded reply to m_007 in Ops Room includes the full list of chats returned by step 1, naming each chat id and name: c_001 "Launch Planning" (group), c_002 (dm), c_003 "Ops Room" (group), and c_004 "Watercooler" (group).
    - where to look: Find this in the text of the reply the agent posted to message m_007 in step 6.

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Please retrieve the full list of chats that the acting user is a member of, then read the most recent messages in the Launch Planning channel and include those message views in your final reply so I can see what was returned. Create a new chat that includes whoever wrote the message about 02:00 I'll be on alongside the acting user. Post a message in that channel whose text contains the complete list of chats you retrieved, showing for each chat its id, its displayed name if any, and whether it is a group or a dm. Post the same complete list in a message to the Ops Room channel; in that same channel post a threaded reply to the message about canary shows increased latencies that also contains the complete list of chats you retrieved. Report back the Launch Planning message views you read and confirm the chat creation and the three outgoing posts in your final reply.
```

### What the judge checks at L2

- **report:c1a0**
    - a correct answer says: A concise summary stating the recent messages read from the Launch Planning channel: the initial message asking to pick the time window (22:00 or 02:00); a reply saying 02:00 is safer for international traffic and to flag the CS team; a reply from whoever wrote the message about 02:00 I'll be on asking someone to draft a clear rollback plan with triggers; and a reply noting that external stakeholders asked for a one-pager.
    - where to look: Look in the agent's final reply where it summarizes or lists the messages returned by reading the Launch Planning channel.
- **carry:c0a1:text**
    - a correct answer says: The message posted to the Launch Planning channel includes the complete list of chats the agent retrieved, with each chat shown by its id, its displayed name (if any), and whether it is a group or a dm — specifically the Launch Planning channel (group), the dm chat, the Ops Room channel (group), and the Watercooler channel (group).
    - where to look: Find this in the text of the message the agent sent to the Launch Planning channel.
- **carry:c1a1:text**
    - a correct answer says: The message posted to the Ops Room channel includes the complete list of chats the agent retrieved, with each chat shown by its id, its displayed name (if any), and whether it is a group or a dm — specifically the Launch Planning channel (group), the dm chat, the Ops Room channel (group), and the Watercooler channel (group).
    - where to look: Find this in the text of the message the agent sent to the Ops Room channel.
- **carry:c0a2:text**
    - a correct answer says: The threaded reply posted in response to the message about canary shows increased latencies includes the complete list of chats the agent retrieved, with each chat shown by its id, its displayed name (if any), and whether it is a group or a dm — specifically the Launch Planning channel (group), the dm chat, the Ops Room channel (group), and the Watercooler channel (group).
    - where to look: Find this in the text of the threaded reply the agent posted to the message about canary shows increased latencies in the Ops Room channel.

## L3 — the goal. No step individually identifiable.

```text
Retrieve the full list of chats the acting user belongs to, and read the most recent messages in the Launch Planning channel; include the messages you read in your final reply so I can verify them. Create a new chat that includes the acting user and whoever wrote the message about 02:00 I'll be on. Post a message in the Launch Planning channel whose text contains the complete list of chats you retrieved, showing for each chat its id, its displayed name if any, and whether it is a group or a dm. Post the same complete list in the Ops Room channel, and in that channel post a threaded reply to the message about canary shows increased latencies that also contains the complete list of chats you retrieved. In your final reply, report back the messages you read from the Launch Planning channel and confirm that you created the new chat and posted the three messages (the message in the Launch Planning channel, the message in the Ops Room channel, and the threaded reply in the Ops Room channel).
```

### What the judge checks at L3

- **report:c1a0**
    - a correct answer says: A concise summary of the recent messages read from the Launch Planning channel that includes: the original request asking to pick the time window for the feature-flag flip (22:00 or 02:00); a reply arguing 02:00 is safer for international traffic and asking to flag the CS team; a reply from whoever wrote the message about 02:00 I'll be on asking someone to draft a clear rollback plan with triggers; and a reply noting that external stakeholders asked for a one-pager.
    - where to look: Look in the agent's final reply where it summarizes or lists the messages returned by reading the Launch Planning channel.
- **carry:c0a1:text**
    - a correct answer says: The message the agent posted to the Launch Planning channel contains the complete list of chats returned by the agent's initial chat listing, with each chat shown by its id, its displayed name if any, and whether it is a group or a dm — specifically listing the Launch Planning channel (group), the dm chat, the Ops Room channel (group), and the Watercooler channel (group).
    - where to look: Find this content in the text of the message the agent sent to the Launch Planning channel.
- **carry:c1a1:text**
    - a correct answer says: The message the agent posted to the Ops Room channel contains the complete list of chats returned by the agent's initial chat listing, with each chat shown by its id, its displayed name if any, and whether it is a group or a dm — specifically listing the Launch Planning channel (group), the dm chat, the Ops Room channel (group), and the Watercooler channel (group).
    - where to look: Find this content in the text of the message the agent sent to the Ops Room channel.
- **carry:c0a2:text**
    - a correct answer says: The threaded reply the agent posted in response to the message about canary shows increased latencies contains the complete list of chats returned by the agent's initial chat listing, with each chat shown by its id, its displayed name if any, and whether it is a group or a dm — specifically listing the Launch Planning channel (group), the dm chat, the Ops Room channel (group), and the Watercooler channel (group).
    - where to look: Find this content in the text of the threaded reply the agent posted to the message about canary shows increased latencies in the Ops Room channel.

## L4 — folded. Actions that existed only to feed each other become one request, no content is dictated word for word, and no clause narrates a hand-off.

```text
Please do this end-to-end: list every chat I'm a member of and read the most recent messages in the Launch Planning channel. Start a new chat that includes me and the person who said they'd be on call if we flip at 02:00. Post the full chat list you retrieved — for each chat show its id, its displayed name if any, and whether it's a group or a dm — as a message in the Launch Planning channel. Post that same full chat list as a message in the Ops Room channel, and also post that same full chat list as a threaded reply to the Ops Room message that reported increased canary latency. In your final reply here, include a concise summary of the messages you read from Launch Planning and confirm that you created the new chat and posted the three messages (the message in Launch Planning, the message in Ops Room, and the threaded reply in Ops Room).
```

### What the judge checks at L4

- **report:c1a0**
    - a correct answer says: A concise summary of the recent messages read from the Launch Planning channel that includes: the original request asking to pick the time window for the feature-flag flip (22:00 or 02:00); a reply arguing 02:00 is safer for international traffic and asking to flag the CS team; a reply from the person who said they'd be on call if we flip at 02:00 asking someone to draft a clear rollback plan with triggers; and a reply noting that external stakeholders asked for a one-pager.
    - where to look: Look in the agent's final reply where it summarizes or lists the messages read from the Launch Planning channel.
- **carry:c0a1:text**
    - a correct answer says: The message posted to the Launch Planning channel contains the complete list of chats returned by the initial chat listing, with each chat shown by its id, its displayed name if any, and whether it is a group or a dm — specifically listing the Launch Planning channel (group), the dm chat, the Ops Room channel (group), and the Watercooler channel (group).
    - where to look: Find this content in the text of the message the agent sent to the Launch Planning channel.
- **carry:c1a1:text**
    - a correct answer says: The message posted to the Ops Room channel contains the complete list of chats returned by the initial chat listing, with each chat shown by its id, its displayed name if any, and whether it is a group or a dm — specifically listing the Launch Planning channel (group), the dm chat, the Ops Room channel (group), and the Watercooler channel (group).
    - where to look: Find this content in the text of the message the agent sent to the Ops Room channel.
- **carry:c0a2:text**
    - a correct answer says: The threaded reply posted in response to the Ops Room canary-latency message contains the complete list of chats returned by the initial chat listing, with each chat shown by its id, its displayed name if any, and whether it is a group or a dm — specifically listing the Launch Planning channel (group), the dm chat, the Ops Room channel (group), and the Watercooler channel (group).
    - where to look: Find this content in the text of the threaded reply the agent posted to the canary-latency message in the Ops Room channel.

## Warnings recorded for this task

- v3: pasted the description 'the Launch Planning channel' 4 times; introduce a thing once, then refer back to it
- v3: pasted the description 'the Ops Room channel' 3 times; introduce a thing once, then refer back to it
- v3: 1 sequencing connective(s) — reads as a list in prose clothing
- v4: pasted the description 'the Launch Planning channel' 2 times; introduce a thing once, then refer back to it
