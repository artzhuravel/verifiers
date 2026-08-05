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
| `$chat_0` | group 'Site Redesign' — members: Sam Lee @you, Alice Moreno @ali | `c_001` | "the Site Redesign channel" | 3/3 |
| `$user_0` | Carla Nguyen @carla.n | `u_carla_n` | "whoever wrote the message about still want to run" | 1/1 |
| `$chat_1` | dm (unnamed dm) — members: Sam Lee @you, Ben Ortiz @ben.o | `c_002` | "the conversation where green for the press came up" | 1/1 |
| `$message_0` | in c_002 from Ben Ortiz, unread by you: "Also: can you publish t | `m_009` | "the message about publish the updated event" | 1/1 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Call list_chats and return the list of chats the acting user is a member of (use the list_chats tool).  
2. Read the most recent messages in chat c_001 (Site Redesign) and return them oldest-to-newest (use the read_messages tool for chat_id=c_001).  
3. Create a new chat that includes Carla Nguyen (user id u_carla_n) as a member (use the create_chat tool with member_ids=["u_carla_n"]).  
4. Send a message to chat c_001 whose text includes a natural-language summary of the chats returned by step 1 (state which chats you are in, including each chat id and name, in normal prose; do not paste raw JSON).  
5. Send a message to chat c_002 whose text includes a natural-language summary of the chats returned by step 1 (state which chats you are in, including each chat id and name, in normal prose; do not paste raw JSON).  
6. Reply to message m_009 in its chat with a message whose text includes a natural-language summary of the chats returned by step 1 (state which chats you are in, including each chat id and name, in normal prose; do not paste raw JSON).  
7. In your final reply to me (after performing the above steps), include a concise summary of the messages you read in step 2 (the recent messages in c_001).
```

### What the judge checks at L1

- **report:c1a0**
    - a correct answer says: A concise summary that lists the recent messages in the Site Redesign chat (c_001), identifying each message by who sent it and its main content: m_001 from Alice Moreno asking to lock the hero layout by Friday and noting a traffic dip; m_002 from Carla Nguyen saying she wants to run one more A/B with variant B and that content needs another day; m_003 from Dan Kim flagging an image parity issue on mobile affecting layout by about 8px; m_006 from Carla Nguyen asking whether the header font load is affecting CLS; m_007 from Sam Lee saying you will consolidate feedback after Friday's review; m_010 from Alice offering to take the analytics pull; m_011 from Carla asking the estimated conversion delta if the hero is delayed; m_013 from Dan suggesting a temporary mobile fix if QA signs off; and m_014 from Alice asking someone to pull analytics for the last two weeks.
    - where to look: Look in the agent's final reply where it summarizes the messages read from chat c_001 (Site Redesign).
- **carry:c0a1:text**
    - a correct answer says: The message posted to chat c_001 includes a natural-language statement that you are a member of these chats: Site Redesign (id c_001), an unnamed DM (id c_002), and Lunch Run (id c_003).
    - where to look: Look at the message the agent sent to chat c_001 (step 4).
- **carry:c1a1:text**
    - a correct answer says: The message posted to chat c_002 includes a natural-language statement that you are a member of these chats: Site Redesign (id c_001), an unnamed DM (id c_002), and Lunch Run (id c_003).
    - where to look: Look at the message the agent sent to chat c_002 (step 5).
- **carry:c0a2:text**
    - a correct answer says: The reply posted to message m_009 includes a natural-language statement that you are a member of these chats: Site Redesign (id c_001), an unnamed DM (id c_002), and Lunch Run (id c_003).
    - where to look: Look at the threaded reply the agent posted to message m_009 (step 6).

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Please list the chats the acting user is a member of and return that list. Then read the most recent messages in the Site Redesign channel and return them oldest to newest. Next create a new chat that includes whoever wrote the message about still want to run as a member. Then send a message to the Site Redesign channel whose text includes a natural-language summary of the chats returned by your initial list, stating which chats you are in and including each chat id and name in normal prose without pasting raw JSON. Then send a message to the conversation where green for the press came up whose text includes a natural-language summary of the chats returned by your initial list, stating which chats you are in and including each chat id and name in normal prose without pasting raw JSON. Then reply to the message about publish the updated event in its chat with a message whose text includes a natural-language summary of the chats returned by your initial list, stating which chats you are in and including each chat id and name in normal prose without pasting raw JSON. After performing these actions, report back to me and include a concise summary of the messages you read from the Site Redesign channel.
```

## L3 — the goal. No step individually identifiable.

```text
Gather the current set of chats the acting user belongs to and use that information to drive outreach and a short report: using the retrieved list, read the most recent messages in the Site Redesign channel in chronological order; create a new chat that includes whoever wrote the message about still want to run; post a natural-language summary, derived from the retrieved list and naming each chat’s id and name in prose, to the Site Redesign channel and to the conversation where green for the press came up; reply in-thread to the message about publish the updated event with that same natural-language summary. When finished, confirm the actions you performed and include a concise summary of the messages you read from the Site Redesign channel.
```

## Warnings recorded for this task

- stage 5 dropped: message n8: message 'n8' is from 'n1', who is not in 'c2'
