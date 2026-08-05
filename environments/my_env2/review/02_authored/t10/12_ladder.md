# The ladder — t10

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
| `$chat_0` | group 'frontend-sprint' — members: Sam Ortiz @you, Alice Chen @a | `c_001` | "the frontend-sprint channel" | 3/3 |
| `$message_0` | in frontend-sprint from Marco Ruiz: "Quick request: could someon | `m_004` | "the message about could someone paste the" | 1/1 |
| `$message_1` | in c_002 from Priya Singh, unread by you: 'Can you ask DeepWiki  | `m_009` | "the message about DeepWiki what license and" | 1/1 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Call list_chats and get the list of chats the acting user (u_me) is a member of (this is step 1, id list_chats).  
2. Send a message in chat c_001 (group 'frontend-sprint') with the exact text: "Quick update: I'm checking the repo license/language Priya asked about and will DM her the results. Marco — when you open the PR for fix/header-padding, drop the link here so QA can pull it into their run." (this is step 2, id send_message).  
3. Ask DeepWiki the question for repo facebook/react: "What license and primary language does facebook/react use?" and record the free-text answer it returns (this is step 3, id ask_question).  
4. Mark every message in chat c_001 as read by the acting user (this is step 4, id mark_read).  
5. Reply (thread) to the message created in step 2; use that message's id as the message_id and send the text: "Assigning the header bug to myself for this cycle — Ben, please paste the failing test stack when you fetch it and I’ll take it from there." (this is step 5, id reply_to).  
6. Reply (thread) to message m_004 in chat c_001 (Marco Ruiz's message asking people to paste the list of chats they're in) and in that reply include the full list you got from step 1: list each chat by id, its kind, its display name, and its member user ids (this is step 6, id reply_to).  
7. Reply (thread) to message m_009 in chat c_002 (Priya's DM asking about acme/frontend-utils) and include the answer returned by the DeepWiki query from step 3 about facebook/react (specifically state the license and primary language reported by the ask_question result) in that reply (this is step 7, id reply_to).
```

### What the judge checks at L1

- **carry:c1a2:text**
    - a correct answer says: The reply to m_004 includes the complete list of chats the acting user is in, naming each chat's id, its kind, its display name, and its members: that c_001 is a group named "frontend-sprint" with members u_me, u_alice, u_ben, u_priya, u_marco; that c_002 is a DM (named "c_002") with members u_me and u_priya; and that c_003 is a group named "random-coffee" with members u_me, u_alice, and u_lina.
    - where to look: Look at the text of the message posted as the reply to m_004 (the message created in step 6).
- **carry:c0a2:text**
    - a correct answer says: The reply to m_009 states that the facebook/react repository is licensed under the MIT License and that its primary language is JavaScript.
    - where to look: Look at the text of the message posted as the reply to m_009 (the message created in step 7).

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Obtain the list of chats the acting user is a member of, then post the following message in the frontend-sprint channel: "Quick update: I'm checking the repo license/language Priya asked about and will DM her the results. Marco — when you open the PR for fix/header-padding, drop the link here so QA can pull it into their run." After posting that message, ask DeepWiki the question "What license and primary language does facebook/react use?" and capture the free-text answer it returns. Next, mark every message in the frontend-sprint channel as read by the acting user. Then reply in-thread to the message you posted in the frontend-sprint channel with the text "Assigning the header bug to myself for this cycle — Ben, please paste the failing test stack when you fetch it and I’ll take it from there." Also reply in-thread to the message about could someone paste the and include the full chat list you obtained earlier, listing each chat by id, its kind, its display name, and its member user ids. Finally, reply in-thread to the message about DeepWiki what license and and include the DeepWiki answer you captured about facebook/react, specifically stating the license and primary language reported by that answer.
```

## L3 — the goal. No step individually identifiable.

```text
Retrieve the list of chats the acting user belongs to and then post an update in the frontend-sprint channel saying you are checking the repo license and primary language Priya asked about and will DM her the results, and asking Marco to drop the PR link for fix/header-padding in the channel so QA can pull it into their run. Ask DeepWiki the question 'What license and primary language does facebook/react use?' and capture the free-text answer. Mark every message in the frontend-sprint channel as read by the acting user. Reply in-thread to the message you posted in the frontend-sprint channel assigning the header bug to yourself and asking Ben to paste the failing test stack when he fetches it so you can take it from there. Reply in-thread to the message about could someone paste the with the full chat list you retrieved earlier, listing each chat by id, its kind, its display name, and its member user ids. Reply in-thread to the message about DeepWiki what license and with the DeepWiki answer you captured about facebook/react, explicitly stating the license and the primary language reported in that answer.
```

## Warnings recorded for this task

(none)
