# The ladder — t1

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
| `$chat_0` | group 'infra-team' — members: Alex Chen @you, Sam Ortega @sam_o, | `c_002` | "the one conversation you still have not caught up on"  **[the work makes this false]** | 4/4 |
| `$message_0` | in infra-team from Lina Wu, replying to m_001: 'Proposed repo: a | `m_004` | "the message about someone confirm its license" | 1/1 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Call read_messages on chat_id c_002 (the infra-team group) and read the most recent messages oldest to newest; keep the full array of message views that the call returns for later steps. 2. Call ask_question on repoName 'apache/cassandra' with the question: "What is this project for, and what's its primary programming language?" and keep the free-text answer the call returns for later steps. 3. Call mark_read on chat_id c_002 so every message in that chat is marked read by the acting user. 4. Call send_message to chat_id c_002 and post a message whose text CARRIES what step 1 returned: the message body must include the sender and text for each message returned by your read_messages call in step 1 (i.e., reproduce or summarize each returned message's sender and message text so the chat thread clearly shows the contents of the messages you read). 5. Call reply_to on message_id m_004 (Lina Wu's message about "Proposed repo: apache/cool-db...") and post a reply whose text CARRIES what step 2 returned: include the full free-text answer returned by your ask_question in step 2 in the body of this threaded reply. 6. Call reply_to on the message created in step 4 and post the exact text: "Happy to run DeepWiki on any other repos on the checklist—tell me which ones."
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: The message posted to chat c_002 in step 4 includes the content of the messages read in step 1 by naming each message's sender and reproducing each message's text (for example, it mentions Sam Ortega's heads-up about the security audit and the need to collect license/primary language/maintainer lists, Marisa's offer to check licenses, Lina's proposal of apache/cool-db and request to confirm license/language/maintainers, Raj's note about Apache-2.0 and Java, and the subsequent checklist/maintainer requests).
    - where to look: Look at the text of the message created by the send_message call in step 4 (the message posted to chat c_002).
- **carry:c1a1:text**
    - a correct answer says: The reply to message m_004 posted in step 5 states that apache/cassandra is a distributed NoSQL database for handling large-scale data with high availability and that its primary programming language is Java.
    - where to look: Look at the text of the reply created by the reply_to call in step 5 (the threaded reply to m_004).

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Please read the most recent messages in the one conversation you still have not caught up on, oldest to newest, and keep the full array of message views that this reading returns for use in later actions. Using the AI-grounded repository question tool, ask about the GitHub repository 'apache/cassandra' the question "What is this project for, and what's its primary programming language?" and keep the free-text answer that tool returns for later use. Then mark every message in the one conversation you still have not caught up on as read by you. Next post a message to the one conversation you still have not caught up on whose text carries what you kept from the first read: the message body must include the sender and text for each message returned by that read so the thread clearly shows their contents. Then reply to the message about someone confirm its license with a threaded reply whose text carries what you kept from the repository-question tool: include the full free-text answer you received. Finally, reply in thread to the message you posted earlier to the one conversation you still have not caught up on with the exact text: "Happy to run DeepWiki on any other repos on the checklist—tell me which ones." Report back in that same conversation.
```

## L3 — the goal. No step individually identifiable.

```text
Bring the one conversation you still have not caught up on up to date by collecting and sharing its recent messages and the result of a DeepWiki lookup. Read the most recent messages in the one conversation you still have not caught up on, oldest to newest, and retain the full array of message views returned for later use. Use the AI-grounded repository question tool to ask about 'apache/cassandra' the question "What is this project for, and what's its primary programming language?" and keep the free-text answer returned. Mark every message in the one conversation you still have not caught up on as read by you. Post a message to the one conversation you still have not caught up on whose body reproduces the sender and text for each message from the retained read so the thread clearly shows their contents. Reply in thread to the message about someone confirm its license with the full free-text answer you received from the repository query. Reply in thread to the message you posted earlier with the exact offer text saying you are happy to run DeepWiki on any other repos on the checklist and asking which ones to process, and report back in that same conversation that the steps are complete.
```

## Warnings recorded for this task

- stage 5 dropped: message n7: message 'n7' is from 'n1', who is not in 'c2'
- stage 5 dropped: message n5: message 'n5' is from 'n1', who is not in 'c1'
- stage 5 dropped: message n10: message 'n10' is from 'n2', who is not in 'c2'
