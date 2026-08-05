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
| `$chat_0` | group 'infra' — members: Sam Park @you, Alice Nguyen @alice, Ben | `c_001` | "the one conversation you still have not caught up on"  **[the work makes this false]** | 1/1/1 |
| `$message_0` | in infra from Ben Ortiz, replying to m_001, unread by you: "Repo | `m_004` | "the message about confirm whether it's MIT" | 1/1/0 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Call read_messages with chat_id c_001 and read the most recent messages in the infra group (oldest to newest). 2. Call ask_question with repoName 'tensorflow/tensorflow' and question "What is this project's primary purpose?" and keep the full textual answer so you can include it in step 5. 3. Call mark_read with chat_id c_001 to mark every message in the infra chat as read by you. 4. Call send_message to chat c_001; the message text must carry what you read in step 1, so include a concise summary of the infra messages you just read that conveys these facts: the DeepWiki integration PR references acme/deepwiki-bot and maintainers were unsure about the repo license, Carlos said Dina would take a look this afternoon, Ben asked Dina to confirm whether it's MIT or Apache (or something else), Dina said she'd pull the repo and check the LICENSE file, Alice asked someone to run a quick license-check and paste the output here, and Ben noted the CI flaked this morning; after sending, return the created message view. 5. Call reply_to with message_id m_004 and post a reply whose text must carry what step 2 returned, i.e., include the answer you received to "What is this project's primary purpose?" about tensorflow/tensorflow; after replying, return the created reply view. 6. Call reply_to to reply to the message created in step 4 (use the id returned by step 4) with the exact text: 'Thanks — @dina, please paste the LICENSE file contents here when you confirm so we can proceed.' and return the created reply view.
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: The message posted to chat c_001 summarizes the infra thread by saying that the DeepWiki integration PR references acme/deepwiki-bot and maintainers were unsure about the repository license; that Carlos said Dina would take a look this afternoon; that Ben asked Dina to confirm whether the license is MIT, Apache, or something else; that Dina said she would pull the repo and check the LICENSE file; that Alice asked someone to run a quick license-check and paste the output here; and that Ben also mentioned the CI flaked this morning.
    - where to look: Look at the text of the message the agent sends to chat c_001 in step 4 (the send_message result).
- **carry:c1a1:text**
    - a correct answer says: The reply to message m_004 states that TensorFlow's primary purpose is to provide an open-source platform/framework for building, training, and deploying machine learning models (including tools for defining and training neural networks and running inference).
    - where to look: Look at the text of the reply the agent posts to message m_004 in step 5 (the reply_to result).

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Read the most recent messages in the one conversation you still have not caught up on, oldest to newest. Then ask about the GitHub repository tensorflow/tensorflow using exactly the question "What is this project's primary purpose?" and keep the full textual answer so you can include it in a reply. Mark every message in that conversation as read by you. Post a message to that conversation whose text must carry what you read in the first step: include a concise summary of the messages you just read that conveys these facts: the DeepWiki integration PR references acme/deepwiki-bot and maintainers were unsure about the repository license, Carlos said Dina would take a look this afternoon, Ben asked Dina to confirm whether it's MIT or Apache (or something else), Dina said she'd pull the repo and check the LICENSE file, Alice asked someone to run a quick license-check and paste the output here, and Ben mentioned the CI flaked this morning; after sending, return the created message view. Reply to the message about confirm whether it's MIT with a reply whose text must carry the answer you received to "What is this project's primary purpose?" about tensorflow/tensorflow; after replying, return the created reply view. Finally, reply to the message you posted with the exact text 'Thanks — @dina, please paste the LICENSE file contents here when you confirm so we can proceed.' and return the created reply view.
```

### What the judge checks at L2

- **carry:c0a1:text**
    - a correct answer says: The message posted to the one conversation you still have not caught up on summarizes the thread by saying that the DeepWiki integration PR references acme/deepwiki-bot and maintainers were unsure about the repository license; that Carlos said Dina would take a look this afternoon; that Ben asked Dina to confirm whether the license is MIT, Apache, or something else; that Dina said she would pull the repo and check the LICENSE file; that Alice asked someone to run a quick license-check and paste the output here; and that Ben also mentioned the CI flaked this morning.
    - where to look: Look at the text of the message the agent sends to that conversation in the step that posts the summary (the created message view returned by that action).
- **carry:c1a1:text**
    - a correct answer says: The reply to the message about confirm whether it's MIT states that TensorFlow's primary purpose is to provide an open-source platform/framework for building, training, and deploying machine learning models (including tools for defining and training neural networks and running inference).
    - where to look: Look at the text of the reply the agent posts to that message about confirm whether it's MIT (the created reply view returned by that action).

## L3 — the goal. No step individually identifiable.

```text
Bring yourself up to date by reading the most recent messages in the one conversation you still have not caught up on, oldest to newest. Use the AI Q&A tool to ask about the GitHub repository 'tensorflow/tensorflow' the exact question "What is this project's primary purpose?" and keep the full textual answer so you can paste it later. Mark every message in that conversation as read by you. Post a concise summary into that conversation that conveys these facts: the DeepWiki integration PR references acme/deepwiki-bot and maintainers were unsure about the repository license; Carlos said Dina would take a look this afternoon; Ben asked Dina to confirm whether it's MIT, Apache, or something else (the message about confirm whether it's MIT); Dina said she'd pull the repo and check the LICENSE file; Alice asked someone to run a quick license-check and paste the output here; and Ben mentioned the CI flaked this morning. Reply in-thread to that message with the full answer you received about 'tensorflow/tensorflow' so the team has that explanation available. Then reply to the summary you posted with the exact text 'Thanks — @dina, please paste the LICENSE file contents here when you confirm so we can proceed.' Return the created message view for the summary, the created reply view for your reply to that message, and the created reply view for the final reply.
```

### What the judge checks at L3

- **carry:c0a1:text**
    - a correct answer says: The message posted to the one conversation you still have not caught up on summarizes the thread by saying that the DeepWiki integration PR references acme/deepwiki-bot and maintainers were unsure about the repository license; that Carlos said Dina would take a look this afternoon; that Ben asked Dina to confirm whether the license is MIT, Apache, or something else; that Dina said she would pull the repo and check the LICENSE file; that Alice asked someone to run a quick license-check and paste the output here; and that Ben also mentioned the CI flaked this morning.
    - where to look: Look at the text of the message the agent sends to that conversation that posts the summary (the created message view returned by that action).
- **carry:c1a1:text**
    - a correct answer says: The reply to the message about confirm whether it's MIT states that TensorFlow's primary purpose is to provide an open-source platform/framework for building, training, and deploying machine learning models (including tools for defining and training neural networks and running inference).
    - where to look: Look at the text of the reply the agent posts to that message (the created reply view returned by that action).

## L4 — folded. Actions that existed only to feed each other become one request, no content is dictated word for word, and no clause narrates a hand-off.

```text
Catch me up on the one conversation you still have not caught up on: read that conversation's recent messages oldest-to-newest. Use the AI Q&A tool to find out the primary purpose of the GitHub repository 'tensorflow/tensorflow'. Mark every message in that conversation as read. Post a concise summary into that conversation that communicates these facts: the DeepWiki integration PR references acme/deepwiki-bot and the maintainers were unsure about that repository's license; Carlos said Dina would take a look that afternoon; Ben asked Dina to confirm whether the license is MIT, Apache, or something else; Dina said she would pull the repo and check the LICENSE file; Alice asked someone to run a quick license-check and paste the output into the thread; and Ben mentioned the CI flaked that morning. Reply in-thread to the message where Ben asked Dina to confirm the license with the full answer you received about 'tensorflow/tensorflow''s primary purpose so the team has that explanation available in the thread. Then reply to the summary you posted with exactly this text: Thanks — @dina, please paste the LICENSE file contents here when you confirm so we can proceed. Return the created message view for the summary, the created reply view with the AI answer, and the created reply view for the final reply.
```

### What the judge checks at L4

- **carry:c0a1:text**
    - a correct answer says: The summary message posted to that conversation explains that the DeepWiki integration PR references acme/deepwiki-bot and that maintainers were unsure about the repository license; that Carlos said Dina would take a look that afternoon; that Ben asked Dina to confirm whether the license is MIT, Apache, or something else; that Dina said she would pull the repo and check the LICENSE file; that Alice asked someone to run a quick license-check and paste the output into the thread; and that Ben mentioned the CI flaked that morning.
    - where to look: Check the text of the summary message the agent posts to that conversation (the created message view returned by that action).
- **carry:c1a1:text**
    - a correct answer says: The reply posted in-thread to Ben's message asking Dina to confirm the license states that TensorFlow's primary purpose is to provide an open-source platform/framework for building, training, and deploying machine learning models, including tools for defining and training neural networks and running inference.
    - where to look: Check the text of the reply the agent posts in-thread to Ben's message (the created reply view returned by that action).

## Warnings recorded for this task

- the task's own work invalidates: $chat_0 ('the one conversation you still have not caught up on')
- v3: 6 sequencing connective(s) — reads as a list in prose clothing
- v4: 6 sequencing connective(s) — reads as a list in prose clothing
