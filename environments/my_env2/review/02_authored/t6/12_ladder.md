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
| `$message_0` | in infra from Ben Park, replying to m_001, unread by you: "I thi | `m_003` | "the message about README points to a" | 1/1 |
| `$chat_0` | dm (unnamed dm) — members: Sam Cho @you, Alice Nguyen @alice | `c_001` | "the conversation where could you read the came up" | 2/3 |
| `$message_1` | in c_001 from Alice Nguyen, unread by you: 'Sam, could you read  | `m_005` | "the message about could you read the" | 1/1 |
| `$chat_1` | group 'infra' — members: Sam Cho @you, Alice Nguyen @alice, Ben  | `c_002` | "the infra channel" | 3/3 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Call read_wiki_contents with repoName='kubernetes/kubernetes' and save the returned wiki DOCUMENTATION PROSE for use in later steps.
2. Add a reaction '+1:' to message m_003 by calling add_reaction with message_id='m_003' and emoji='+1:'.
3. Send a message to chat c_001 by calling send_message with chat_id='c_001' and set the message text to include the wiki DOCUMENTATION PROSE returned by step 1 in full; the body must carry that prose.
4. Reply to message m_005 in chat c_001 by calling reply_to with message_id='m_005' and text='Done — I pasted the wiki prose into the infra channel and included the lifecycle section verbatim.'
5. Send a message to chat c_002 by calling send_message with chat_id='c_002' and set the message text to include the wiki DOCUMENTATION PROSE returned by step 1 in full; the body must carry that prose.
6. Reply to the message you created in step 5 by calling reply_to with message_id equal to the id of that created message and text='Lifecycle section is verbatim above per Alice. @benp please start extracting config keys; @carl please skim the leader-election section.'
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: The message posted to chat c_001 contains the DeepWiki wiki documentation prose for the kubernetes/kubernetes repository — specifically the repository's documentation describing the project's purpose and explanations of its subsystems (including lifecycle and leader-election material if present).
    - where to look: Look at the text field of the message created by step 3 (the send_message to chat c_001).
- **carry:c0a2:text**
    - a correct answer says: The message posted to chat c_002 contains the DeepWiki wiki documentation prose for the kubernetes/kubernetes repository — specifically the repository's documentation describing the project's purpose and explanations of its subsystems (including lifecycle and leader-election material if present).
    - where to look: Look at the text field of the message created by step 5 (the send_message to chat c_002).

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Please read the DeepWiki documentation for the GitHub repository kubernetes/kubernetes and save the returned wiki DOCUMENTATION PROSE for use in later steps. After that, add a '+1:' reaction to the message about README points to a. Then send a message to the conversation where could you read the came up whose text contains the wiki DOCUMENTATION PROSE returned earlier in full; the message body must carry that prose. Next, reply to the message about could you read the with the text 'Done — I pasted the wiki prose into the infra channel and included the lifecycle section verbatim.' Then send a message to the infra channel whose text contains the same wiki DOCUMENTATION PROSE returned earlier in full; the message body must carry that prose. Finally, reply to the message you created in the infra channel with the text 'Lifecycle section is verbatim above per Alice. @benp please start extracting config keys; @carl please skim the leader-election section.' Please report back in the conversation where could you read the came up.
```

## L3 — the goal. No step individually identifiable.

```text
Obtain the DeepWiki documentation prose for the GitHub repository kubernetes/kubernetes and keep that prose available for the subsequent posts. React with a thumbs-up emoji to the message about README points to a. Post the wiki prose verbatim into the conversation where could you read the came up and also into the infra channel, ensuring the lifecycle section is included verbatim. In the conversation where could you read the came up, reply to the message about could you read the to confirm completion and state that you pasted the wiki prose into the infra channel and included the lifecycle section verbatim. In the infra channel, after posting the same prose, reply in-thread to note the lifecycle section is verbatim and ask Ben Park to extract config keys and Carlos Ruiz to skim the leader-election section. Finally, report back in the conversation where could you read the came up once everything is posted.
```

## Warnings recorded for this task

- stage 5 dropped: message n6: message 'n6' is from 'u2', who is not in 'c1'
