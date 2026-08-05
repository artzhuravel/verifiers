# The ladder — t8

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
| `$user_0` | Benjamin Ortiz @ben | `u_ben` | "whoever wrote the message about someone confirm my GitHub" | 3/3 |
| `$message_0` | in backend-team from Benjamin Ortiz, replying to m_001, unread b | `m_002` | "the message about someone confirm my GitHub" | 5/5 |
| `$message_1` | in c_002 from Carla Ruiz, unread by you: "Hey — can you look up  | `m_007` | "the message about @-mention him in the" | 1/1 |
| `$chat_0` | group 'backend-team' — members: Sam Ortega @you, Alice Monroe @a | `c_001` | "the conversation where before we cut the came up" | 2/2 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Look up the user with id u_ben using get_user and save the returned value for use in later steps. 2. Ask the repository question to the AI-grounded repo tool: "What is the primary purpose of the python/cpython repository?" and save the returned answer; include that returned answer in your final reply. 3. Reply in-thread to message m_002 in the backend-team chat and make the reply text include the value returned by the get_user call from step 1. 4. Reply in-thread to message m_007 in the DM chat and make the reply text include the value returned by the get_user call from step 1. 5. Send a message to chat c_001 (backend-team) whose message text includes the value returned by the get_user call from step 1. 6. Reply in-thread to the message you created in step 3 with exactly: "Thanks — noted Ben's GitHub handle is ben; I'll mention him in the issue and update the release checklist.".
```

### What the judge checks at L1

- **report:c2a0**
    - a correct answer says: The python/cpython repository is the reference implementation of the Python programming language (CPython), containing the interpreter source code and the standard library and tooling to build and ship the Python interpreter.
    - where to look: Look in the agent's final reply for the paragraph that reports the answer returned by the repo question about python/cpython.
- **carry:c0a1:text**
    - a correct answer says: The reply posted to message m_002 explicitly states that Ben's GitHub handle is ben.
    - where to look: Check the text of the reply the agent sent in-thread to message m_002 in the backend-team chat.
- **carry:c1a0:text**
    - a correct answer says: The reply posted to message m_007 explicitly states that Ben's GitHub handle is ben.
    - where to look: Check the text of the reply the agent sent in-thread to message m_007 in the DM with Carla.
- **carry:c0a2:text**
    - a correct answer says: The message sent to chat c_001 (backend-team) explicitly states that Ben's GitHub handle is ben.
    - where to look: Check the text of the new message the agent posted to the backend-team chat (chat id c_001).

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Look up the user who is whoever wrote the message about someone confirm my GitHub and save the returned value for use in later steps, then ask the repository question about python/cpython exactly: "What is the primary purpose of the python/cpython repository?" and save that returned answer and include that returned answer in your final reply; next, reply in-thread to the message about someone confirm my GitHub in the conversation where before we cut the came up and make that reply text include the value returned by the user lookup, and also reply in-thread to the message about @-mention him in the in the DM chat and make that reply text include the value returned by the user lookup; after that send a message to the conversation where before we cut the came up whose message text includes the value returned by the user lookup; finally, reply in-thread to the message you created when replying to the message about someone confirm my GitHub with exactly: "Thanks — noted whoever wrote the message about someone confirm my GitHub's GitHub handle is whoever wrote the message about someone confirm my GitHub; I'll mention him in the issue and update the release checklist."
```

## L3 — the goal. No step individually identifiable.

```text
Look up the user who is whoever wrote the message about someone confirm my GitHub and retain the returned user object for later use; ask the repository question to python/cpython exactly as: "What is the primary purpose of the python/cpython repository?" and save that answer so you can include it in your final reply; reply in-thread to the message about someone confirm my GitHub in the conversation where before we cut the came up with a message that includes the retained user value; reply in-thread to the message about @-mention him in the in the DM with a message that includes the retained user value; send a message to the conversation where before we cut the came up whose body includes the retained user value; finally reply in-thread to the message you created when replying to the message about someone confirm my GitHub with exactly: Thanks — noted whoever wrote the message about someone confirm my GitHub's GitHub handle is whoever wrote the message about someone confirm my GitHub; I'll mention him in the issue and update the release checklist. Make sure the answer returned for "What is the primary purpose of the python/cpython repository?" is included in your final reply.
```

## Warnings recorded for this task

- stage 5 dropped: message n8: message 'n8' is from 'u1', who is not in 'c2'
