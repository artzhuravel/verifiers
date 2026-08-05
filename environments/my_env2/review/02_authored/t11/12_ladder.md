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
| `$user_0` | Alice Park @alice_a | `u_alice_a` | "whoever wrote the message about where are the design" | 2/2 |
| `$user_1` | Ben Soto @ben_b | `u_ben_b` | "whoever wrote the message about They're in the repo" | 2/2 |
| `$message_0` | in backend-team from Ben Soto, replying to m_004, unread by you: | `m_006` | "the reply to the message about someone pull the DeepWiki" | 1/1 |
| `$chat_0` | dm (unnamed dm) — members: Jamie K. @you, Carol Nguyen @carol_c | `c_002` | "the conversation where DeepWiki on acme/event-sourcing and came up" | 2/2 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Run read_wiki_contents on the repository 'acme/event-sourcing' (repoName = 'acme/event-sourcing') and retrieve the repository's documentation prose; keep that prose available for use in later steps.  
2. Run read_wiki_structure on the repository 'acme/event-sourcing' (repoName = 'acme/event-sourcing') and retrieve the list of documentation topic titles; keep that list available for use in later steps.  
3. Create a new chat that includes users u_alice_a and u_ben_b (Alice Park and Ben Soto); note the created chat id for step 6.  
4. Reply to message m_006 in the backend-team chat and in the reply text include the documentation prose you obtained in step 1 — specifically state what the repo documentation says about what the project is for, how the event-sourcing subsystem works, and the meanings of key concepts.  
5. Send a message to chat c_002 (the DM with Carol) whose text carries the list of documentation topic titles you obtained in step 2 by listing those topic titles in the DM to Carol.  
6. Send a message to the chat you created in step 3 with the exact text: 'Alice, Ben — I ran DeepWiki on acme/event-sourcing and shared the page list with Carol; tell me if you want the full pages copied here.'
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: The reply to message m_006 contains the repository's documentation prose describing what acme/event-sourcing is for, how its event-sourcing subsystem works, and explanations of the repository's key concepts.
    - where to look: Look at the message posted as a reply to m_006 in the backend-team chat (the step 4 reply).
- **carry:c1a1:text**
    - a correct answer says: The DM sent to chat c_002 lists the documentation topic titles (the page list) that were returned by read_wiki_structure for acme/event-sourcing.
    - where to look: Look at the message sent to chat c_002 (the DM to Carol) created in step 5.

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Please run DeepWiki on 'acme/event-sourcing' and pull the repository's documentation prose, keeping that prose available for use in the rest of this task, and also run DeepWiki's listing for 'acme/event-sourcing' and pull the list of documentation topic titles, keeping that list available for later use. Create a new chat that includes whoever wrote the message about where are the design and whoever wrote the message about They're in the repo, and note the created chat for the final item below. Reply to the reply to the message about someone pull the DeepWiki and in that reply paste the documentation prose you obtained, specifically stating what the repo documentation says about what the project is for, how the event-sourcing subsystem works, and the meanings of key concepts. Send a message to the conversation where DeepWiki on acme/event-sourcing and came up carrying the list of documentation topic titles you obtained by listing those topic titles in that DM. Finally, post to the chat you created the following text: whoever wrote the message about where are the design, whoever wrote the message about They're in the repo — I ran DeepWiki on acme/event-sourcing and shared the page list with the conversation where DeepWiki on acme/event-sourcing and came up; tell me if you want the full pages copied here.
```

## L3 — the goal. No step individually identifiable.

```text
Run DeepWiki on acme/event-sourcing to retrieve the repository's documentation prose and keep that prose available for later use, and also fetch the list of documentation topic titles and keep that list available. Create a new chat that includes whoever wrote the message about where are the design and whoever wrote the message about They're in the repo, then reply in the reply to the message about someone pull the DeepWiki with the full documentation prose you obtained, explicitly stating what the repo documentation says about what the project is for, how the event-sourcing subsystem works, and the meanings of key concepts. Send the list of documentation topic titles to the conversation where DeepWiki on acme/event-sourcing and came up. Finally, post to the chat you created the following text: whoever wrote the message about where are the design, whoever wrote the message about They're in the repo — I ran DeepWiki on acme/event-sourcing and shared the page list with the conversation where DeepWiki on acme/event-sourcing and came up; tell me if you want the full pages copied here.
```

## Warnings recorded for this task

- stage 5 dropped: message n6: message 'n6' is from 'n1', who is not in 'c1'
- authored content repeats the phrase 'the conversation where DeepWiki on acme/event-sourcing and came up'
