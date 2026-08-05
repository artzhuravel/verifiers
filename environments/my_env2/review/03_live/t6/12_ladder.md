# The ladder — t6

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
| `$message_0` | in telemetry from Ben Rosario, replying to m_001, unread by you: | `m_002` | "the reply to the message about worried about bursts if" | 1/1/1 |
| `$chat_0` | dm (unnamed dm) — members: You @you, Alice Chen @alicec | `c_002` | "the conversation where DeepWiki export docs and came up" | 1/1/0 |
| `$message_1` | in infra from Diego Patel, unread by you: "Infra question: what  | `m_008` | "the message about chunk size should we" | 1/1/1 |
| `$chat_1` | group 'infra' — members: You @you, Ben Rosario @benr, Diego Pate | `c_003` | "the infra channel" | 1/2/1 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Read the DeepWiki documentation prose for the repository 'kubernetes/kubernetes' by calling read_wiki_contents(repoName='kubernetes/kubernetes') and keep the returned wiki documentation prose (the text that states what the project is for, how a subsystem works, and what a concept means) available for use in later steps.
2. Add a ':+1:' reaction from you to the existing message m_002 in group telemetry.
3. Send a message in the DM chat c_002 to Alice (chat_id = c_002) whose message text must carry the wiki documentation prose you retrieved in step 1, i.e., include that documentation prose verbatim or quoted in the body of the message you post.
4. Reply to message m_008 in the infra group with the exact text: "Default to ~64MB chunks and require client exponential backoff plus idempotency tokens to avoid repeated retries."
5. Send a message to the infra group (chat_id = c_003) whose message text must carry the wiki documentation prose you retrieved in step 1, i.e., include that documentation prose verbatim or quoted in the body of the message you post.
6. Reply to the message you created in step 5 with the exact text: "If we lock 64MB + client backoff, I can update the pipeline defaults and add a retransmit test."
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: The DM message posted to chat c_002 contains the repository's wiki documentation prose describing what the kubernetes project is for and explaining how a subsystem works and what the concept means.
    - where to look: Check the body text of the message the agent sends to chat c_002 (the DM) in step 3.
- **carry:c0a2:text**
    - a correct answer says: The message posted to the infra group (chat c_003) contains the repository's wiki documentation prose describing what the kubernetes project is for and explaining how a subsystem works and what the concept means.
    - where to look: Check the body text of the message the agent sends to chat c_003 (the infra group) in step 5.

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Pull the DeepWiki wiki documentation prose for the repository 'kubernetes/kubernetes' and keep that prose available for use in later posts; it should be the text that states what the project is for, how a subsystem works, and what a concept means. Then add a ':+1:' emoji reaction from you to the reply to the message about worried about bursts if. Next, send a message in the conversation where DeepWiki export docs and came up; the body of that message must carry the wiki documentation prose you retrieved (include it verbatim or quoted). After that, reply in the infra channel to the message about chunk size should we with the exact text: "Default to ~64MB chunks and require client exponential backoff plus idempotency tokens to avoid repeated retries." Then post to that same infra channel a message whose body must carry the same wiki documentation prose you retrieved. Finally, reply to the message you just posted in that channel with the exact text: "If we lock 64MB + client backoff, I can update the pipeline defaults and add a retransmit test."
```

### What the judge checks at L2

- **carry:c0a1:text**
    - a correct answer says: The message the agent posts in the conversation where DeepWiki export docs and came up contains the repository's wiki documentation prose describing what the kubernetes project is for and explaining how a subsystem works and what the concept means.
    - where to look: Check the body text of the message the agent sends to the conversation where DeepWiki export docs and came up (the DM) that carries the wiki documentation prose.
- **carry:c0a2:text**
    - a correct answer says: The message posted to the infra channel contains the repository's wiki documentation prose describing what the kubernetes project is for and explaining how a subsystem works and what the concept means.
    - where to look: Check the body text of the message the agent sends to the infra channel that carries the wiki documentation prose.

## L3 — the goal. No step individually identifiable.

```text
Retrieve the DeepWiki wiki documentation prose for kubernetes/kubernetes and keep that prose ready to paste verbatim into messages you will send. Add a :+1: reaction from me to the reply to the message about worried about bursts if. Post the retrieved wiki prose into the conversation where DeepWiki export docs and came up; that conversation is the DM with Alice, so send a new message there whose body contains the wiki documentation prose you fetched. In the infra channel, reply to the message about chunk size should we with this exact line: Default to ~64MB chunks and require client exponential backoff plus idempotency tokens to avoid repeated retries. After that, post a new message in the infra channel whose body contains the same wiki documentation prose you fetched, and reply to that newly created message with this exact line: If we lock 64MB + client backoff, I can update the pipeline defaults and add a retransmit test.
```

### What the judge checks at L3

- **carry:c0a1:text**
    - a correct answer says: The DM sent to the conversation where DeepWiki export docs and came up contains the repository kubernetes/kubernetes wiki documentation prose that describes what the project is for and explains how a subsystem works and what the concept means.
    - where to look: Look at the body text of the new message posted to the conversation where DeepWiki export docs and came up (the DM) and verify it contains the kubernetes/kubernetes wiki documentation prose that explains the project's purpose and describes subsystem and concept details.
- **carry:c0a2:text**
    - a correct answer says: The message posted to the infra channel contains the repository kubernetes/kubernetes wiki documentation prose that describes what the project is for and explains how a subsystem works and what the concept means.
    - where to look: Check the body text of the new message posted in the infra channel and verify it contains the kubernetes/kubernetes wiki documentation prose describing the project's purpose and explaining subsystem and concept details.

## L4 — folded. Actions that existed only to feed each other become one request, no content is dictated word for word, and no clause narrates a hand-off.

```text
Pull the DeepWiki wiki documentation prose for kubernetes/kubernetes. Then do the following as me:

- Add a :+1: reaction to Ben's reply that mentioned the DeepWiki exporter chunking docs (the reply to the message about worried about bursts if).
- Post the retrieved wiki prose as a new message in the DM with Alice where we first brought up the DeepWiki export docs (the conversation where DeepWiki export docs came up).
- In the infra channel, reply to Diego's question about chunk size (the message about chunk size should we) with this exact line: Default to ~64MB chunks and require client exponential backoff plus idempotency tokens to avoid repeated retries.
- Still in infra, post a new message containing the same kubernetes/kubernetes wiki prose you fetched.
- Reply to that new infra message with this exact line: If we lock 64MB + client backoff, I can update the pipeline defaults and add a retransmit test.

Perform all reactions and posts as me.
```

### What the judge checks at L4

- **carry:c0a1:text**
    - a correct answer says: The DM sent to the Alice DM (the conversation where we discussed the DeepWiki export docs) contains the kubernetes/kubernetes wiki documentation prose that explains what the project is for and that describes how a subsystem works and what the concept means.
    - where to look: Look at the body text of the new message posted to the DM with Alice (the conversation where DeepWiki export docs came up) and verify it contains the kubernetes/kubernetes wiki documentation prose describing the project's purpose and explaining subsystem and concept details.
- **carry:c0a2:text**
    - a correct answer says: The message posted in the infra channel contains the kubernetes/kubernetes wiki documentation prose that explains what the project is for and that describes how a subsystem works and what the concept means.
    - where to look: Check the body text of the new message posted in the infra channel and verify it contains the kubernetes/kubernetes wiki documentation prose describing the project's purpose and explaining subsystem and concept details.

## Warnings recorded for this task

- v3: pasted the description 'the infra channel' 2 times; introduce a thing once, then refer back to it
- v3: 1 sequencing connective(s) — reads as a list in prose clothing
- v4: still enumerates 5 step(s)
- v4: 1 sequencing connective(s) — reads as a list in prose clothing
