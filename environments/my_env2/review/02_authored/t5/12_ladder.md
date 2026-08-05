# The ladder — t5

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
| `$message_0` | in platform-infra from Ben Olad, replying to m_001, unread by yo | `m_002` | "the message about quick listing later today" | 2/2 |
| `$message_1` | in doc-review from Ben Olad, replying to m_003, unread by you: " | `m_008` | "the latest thing @beno posted" | 2/1 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Call read_wiki_structure with repoName 'acme/platform' and record the list of documentation topic titles it returns. 2. Call list_chats and record the array of chats (id, kind, name, and members) it returns. 3. Reply to message m_002 with the text: 'Confirmed — the repo is acme/platform. Ben, please run DeepWiki against acme/platform and paste the topic list here when you have it.' 4. Reply to message m_008 with a message that carries what step 2 and step 1 returned: include the DeepWiki documentation topic titles you recorded for acme/platform and include the list_chats output (each chat's id, kind, name, and members). 5. Add the ':+1:' reaction to the message you created in step 4. 6. Reply to message m_002 with a message that carries what step 2 returned: include the list_chats output (each chat's id, kind, name, and members).
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: The reply to m_008 includes the DeepWiki documentation topic titles for acme/platform and also lists the three chats the acting user is in: c_001 (platform-infra) with members u_me, u_alicec, u_beno, u_cruiz; c_002 (doc-review) with members u_me, u_beno, u_dpark; and c_003 (coffee-break) with members u_me, u_alicec, u_ekim.
    - where to look: Look at the text of the message posted as the reply to m_008 (the message created in step 4). It should contain the DeepWiki topic titles and the full list_chats output (ids, names/kinds, and members).
- **carry:c1a1:text**
    - a correct answer says: The reply to m_002 includes the list of chats the acting user is in, specifically the three chats: c_001 (platform-infra) with members u_me, u_alicec, u_beno, u_cruiz; c_002 (doc-review) with members u_me, u_beno, u_dpark; and c_003 (coffee-break) with members u_me, u_alicec, u_ekim.
    - where to look: Look at the text of the message posted as the reply to m_002 in step 6; it should contain the list_chats output (each chat's id, kind/name, and member lists).

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Call DeepWiki's documentation-topic listing for the GitHub repository 'acme/platform' and record the list of documentation topic titles it returns. Obtain the list of chats the acting user is a member of and record the array of chats returned, ensuring you capture each chat's id, kind, name, and members. Reply in-thread to the message about quick listing later today with the text: 'Confirmed — the repo is acme/platform. Ben, please run DeepWiki against acme/platform and paste the topic list here when you have it.' Reply in-thread to the latest thing @beno posted with a message that carries what you recorded from the previous two reads: include the DeepWiki documentation topic titles you recorded for acme/platform and include the array of chats you recorded, listing each chat's id, kind, name, and members. Add the ':+1:' reaction to the message you create replying to the latest thing @beno posted. Finally, reply in-thread to the message about quick listing later today with a message that carries the array of chats you recorded (each chat's id, kind, name, and members).
```

## L3 — the goal. No step individually identifiable.

```text
Gather the documentation topic titles DeepWiki returns for the GitHub repository 'acme/platform' and record that list along with the array of chats you are a member of, capturing each chat's id, kind, name, and members. In the thread of the message about quick listing later today confirm the repo as acme/platform and ask Ben to run DeepWiki against it and paste the topic list there. In the thread of the latest thing @beno posted, publish the collected DeepWiki topic titles together with the captured chat array and add a ':+1:' reaction to that new post. Also post the captured chat array in the thread of the message about quick listing later today.
```

## Warnings recorded for this task

(none)
