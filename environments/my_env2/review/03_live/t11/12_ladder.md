# The ladder — t11

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
| `$user_0` | Priya Sinha @pri | `u_pri` | "whoever wrote the message about payment-service runbook with the" | 1/1/0 |
| `$user_1` | Marco Li @marco | `u_marco` | "whoever wrote the message about interested in architecture and" | 1/1/0 |
| `$message_0` | in backend-team from Priya Sinha, unread by you: 'Heads-up: We n | `m_001` | "the message about payment-service runbook with the" | 2/2/2 |
| `$chat_0` | dm (unnamed dm) — members: Sam Harper @you, Owen Brooks @owen | `c_002` | "the conversation where pushed a small update came up" | 1/1/1 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Call read_wiki_contents with repoName='owner/acme/payment-service' and keep the returned documentation prose (the prose describing what the project is for, how subsystems work, and definitions of key concepts) available for use in later steps.
2. Call read_wiki_structure with repoName='owner/acme/payment-service' and keep the returned list of documentation topic titles available for use in later steps.
3. Create a new chat by calling create_chat with member_ids=[u_pri, u_marco] (the acting user is added automatically) and keep the created chat id for step 6.
4. Reply to message m_001 in the backend-team chat by calling reply_to with message_id='m_001' and a reply text that carries the main points from the documentation prose you read in step 1 — in other words, summarize the wiki prose for owner/acme/payment-service so the thread can use it (state what the project is for, explain how a relevant subsystem works, and include any key concept definitions you found).
5. Send a message to the DM chat c_002 by calling send_message with chat_id='c_002' and a message text that carries the list of documentation topic titles you obtained in step 2 — present the topic titles as a clear list so Owen can see which wiki topics exist for owner/acme/payment-service.
6. Send a message to the chat created in step 3 by calling send_message with chat_id equal to the id returned by step 3 and with the exact text: "Thanks — I pasted the docs into Priya's thread. Priya, can you lead the runbook review; Marco, can you check architecture and API and flag any issues by Thursday?"
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: The reply to m_001 summarizes the payment-service wiki documentation prose, stating what the owner/acme/payment-service project is for, explaining how at least one subsystem works, and defining or explaining key concepts from the docs.
    - where to look: Look in the reply message you post as a reply to message m_001 in the backend-team chat (the message created in step 4).
- **carry:c1a1:text**
    - a correct answer says: The DM sent to chat c_002 lists the repository's documentation topic titles as a clear list of topic names (the wiki's topic titles that describe the areas the docs cover, such as Architecture, Runbook, API, etc.).
    - where to look: Look in the message you send to chat c_002 (the DM to Owen) created in step 5.

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Fetch the DeepWiki documentation prose for owner/acme/payment-service and keep it available for use; also fetch the list of documentation topic titles for owner/acme/payment-service and keep that available. Create a new chat that includes whoever wrote the message about payment-service runbook with the, whoever wrote the message about interested in architecture and, and me. Post a reply in the backend-team thread to the message that is the message about payment-service runbook with the; that reply must carry the main points from the documentation prose you fetched, summarizing what the owner/acme/payment-service project is for, explaining how at least one relevant subsystem works, and including any key concept definitions from the docs. Send a direct message into the conversation where pushed a small update came up that lists the repository's documentation topic titles as a clear list of topic names so the other participant there can see which wiki topics exist for owner/acme/payment-service. Finally, send a message to the chat you created with the exact text: "Thanks — I pasted the docs into Priya's thread. Priya, can you lead the runbook review; Marco, can you check architecture and API and flag any issues by Thursday?"
```

### What the judge checks at L2

- **carry:c0a1:text**
    - a correct answer says: The reply to the message about payment-service runbook with the summarizes the payment-service wiki documentation prose, stating what the owner/acme/payment-service project is for, explaining how at least one subsystem works, and defining or explaining key concepts from the docs.
    - where to look: Look in the reply message you post as a reply to the message about payment-service runbook with the in the backend-team chat (the reply created in that thread).
- **carry:c1a1:text**
    - a correct answer says: The DM you send to the conversation where pushed a small update came up lists the repository's documentation topic titles as a clear list of topic names (for example: Architecture, Runbook, API).
    - where to look: Look in the message you send to the conversation where pushed a small update came up (the direct message you create).

## L3 — the goal. No step individually identifiable.

```text
Goal: bring the DeepWiki content for 'owner/acme/payment-service' into our team conversations so the runbook sync can proceed. Fetch the wiki documentation prose for 'owner/acme/payment-service' and fetch the list of documentation topic titles for the same repo. Create a new chat that includes whoever wrote the message about payment-service runbook with the, whoever wrote the message about interested in architecture and, and me. In the backend-team thread, post a reply to the message identified as the message about payment-service runbook with the that carries the main points from the documentation prose you fetched: state what the 'owner/acme/payment-service' project is for, explain how at least one relevant subsystem works, and include definitions or explanations of key concepts the docs define. Send a direct message into the conversation where pushed a small update came up that lists the repository's documentation topic titles as a clear list of topic names (for example: Architecture, Runbook, API). Finally, send a message to the chat you created with this exact text: "Thanks — I pasted the docs into Priya's thread. Priya, can you lead the runbook review; Marco, can you check architecture and API and flag any issues by Thursday?"
```

### What the judge checks at L3

- **carry:c0a1:text**
    - a correct answer says: The reply posted in the backend-team thread in response to the message about payment-service runbook with the summarizes the payment-service wiki documentation prose: it states what the owner/acme/payment-service project is for, explains how at least one subsystem works, and defines or explains key concepts appearing in the docs.
    - where to look: Check the reply message you post in that backend-team thread in response to the message about payment-service runbook with the (the threaded reply you create).
- **carry:c1a1:text**
    - a correct answer says: The direct message you send to the conversation where pushed a small update came up contains a clear list of the repository's documentation topic titles (the wiki topic names for owner/acme/payment-service, e.g. Architecture, Runbook, API).
    - where to look: Look at the message you send to the conversation where pushed a small update came up (the DM you create) to find the listed topic titles.

## L4 — folded. Actions that existed only to feed each other become one request, no content is dictated word for word, and no clause narrates a hand-off.

```text
Please bring the DeepWiki content for owner/acme/payment-service into our team conversations so the runbook sync can proceed.

- Fetch the repository's wiki documentation prose for owner/acme/payment-service and produce a short summary that: states what the project is for, explains how at least one relevant subsystem works, and includes definitions or explanations of any key concepts the docs define.

- Fetch the repository's wiki topic list for owner/acme/payment-service and produce a clear list of the topic titles (the wiki page names).

- Create a new group chat that includes me plus the author of the message about payment-service runbook with the and the author of the message about interested in architecture and.

- In the backend-team thread, post a threaded reply to the message about payment-service runbook with the that contains the summary you made from the repository's documentation prose (include the project purpose, one subsystem explanation, and key concept definitions).

- Send a direct message into the conversation where pushed a small update came up that contains the repository's documentation topic titles as a clear list (one title per line or a short bulleted list).

- In the new chat you created, post a follow-up message saying you pasted the docs into that thread and asking the author of the runbook request to lead the review and asking the author who offered to check architecture and API to flag any issues by Thursday.
```

### What the judge checks at L4

- **carry:c0a1:text**
    - a correct answer says: A threaded reply posted in the backend-team conversation in response to the message about payment-service runbook with the that summarizes the repository's wiki documentation prose: it states what owner/acme/payment-service is for, explains how at least one relevant subsystem works, and defines or explains key concepts that appear in the docs.
    - where to look: Check the threaded reply you posted in the backend-team thread in response to the message about payment-service runbook with the; that reply should contain the project purpose, a subsystem explanation, and key concept definitions.
- **carry:c1a1:text**
    - a correct answer says: A direct message sent into the conversation where pushed a small update came up that lists the repository's documentation topic titles as a clear list of topic names (the wiki page titles for owner/acme/payment-service).
    - where to look: Look at the direct message you sent to the conversation where pushed a small update came up; it should contain the list of wiki topic titles (one per line or a short bulleted list).

## Warnings recorded for this task

- stage 5 dropped: message n10: message 'n10' is from 'u1', who is not in 'c2'
- v2: named 'marco'
- v2: pasted the description 'the message about payment-service runbook with the' 2 times; introduce a thing once, then refer back to it
- v3: named 'marco'
- v3: pasted the description 'the message about payment-service runbook with the' 2 times; introduce a thing once, then refer back to it
- v3: 1 sequencing connective(s) — reads as a list in prose clothing
- v4: pasted the description 'the message about payment-service runbook with the' 2 times; introduce a thing once, then refer back to it
- v4: still enumerates 6 step(s)
