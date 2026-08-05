# The ladder — t4

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
| `$message_0` | in infra-team from Alice Morgan, unread by you: "Security flagge | `m_001` | "the message about Security flagged dependency 'belmont/cache" | 2/1 |
| `$chat_0` | group 'infra-team' — members: Sam Ortiz @you, Alice Morgan @alic | `c_001` | "the infra-team channel" | 3/2 |
| `$chat_1` | dm (unnamed dm) — members: Sam Ortiz @you, David Park @dpark | `c_002` | "the conversation where Security pinged me about came up" | 1/1 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Use ask_question on repo 'rails/rails' with the question: "What is this project's purpose and what is its primary programming language?".
2. Reply to message m_001 in chat c_001 with the text: "I'll take this — I'll scan belmont/cache (v1.4.1) and post a short summary (license, primary programming language, maintainer/contact) here by EOD.".
3. Reply to the message you created in step 2 with the text: "Starting the scan now; will update this thread with the short summary when it's ready.".
4. Send a message to chat c_001 (infra-team) whose message text includes the exact answer returned by step 1; include that answer verbatim in the message body so the thread contains the result of the ask_question call.
5. Reply to message m_001 in chat c_001 with the text: "Summary posted in this thread and I DM'd David a copy.".
6. Add the ':+1:' reaction to the message you posted in step 3 (the "Starting the scan now; will update this thread with the short summary when it's ready." reply).
7. Send a message to chat c_002 (the DM with David Park) whose message text includes the exact answer returned by step 1; include that answer verbatim in the message body so David receives the same ask_question result.
```

### What the judge checks at L1

- **carry:c1a0:text**
    - a correct answer says: The Ruby on Rails project is a server-side web application framework for building web applications, and its primary programming language is Ruby.
    - where to look: Look in the message you send to chat c_001 in step 4; the message body should contain this information.
- **carry:c1a2:text**
    - a correct answer says: The Ruby on Rails project is a server-side web application framework for building web applications, and its primary programming language is Ruby.
    - where to look: Look in the message you send to chat c_002 (the DM to David) in step 7; the message body should contain this information.

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
First, ask an AI-grounded question about the GitHub repository 'rails/rails' with the question: "What is this project's purpose and what is its primary programming language?". Then reply to the message about Security flagged dependency 'belmont/cache in the infra-team channel with the text: "I'll take this — I'll scan belmont/cache (v1.4.1) and post a short summary (license, primary programming language, maintainer/contact) here by EOD." Then reply to the message you created with the text: "Starting the scan now; will update this thread with the short summary when it's ready." Then send a message to the infra-team channel whose message text includes the exact answer returned by the first action; include that answer verbatim in the message body so the thread contains the result of the AI-grounded question. Then reply to the message about Security flagged dependency 'belmont/cache in the infra-team channel with the text: "Summary posted in this thread and I DM'd David a copy." Then add the ':+1:' reaction to the message you posted that reads "Starting the scan now; will update this thread with the short summary when it's ready." Finally, send a message to the conversation where Security pinged me about came up whose message text includes the exact answer returned by the first action; include that answer verbatim so David receives the same result.
```

## L3 — the goal. No step individually identifiable.

```text
Obtain a concise, authoritative description of the repository rails/rails by asking the AI-grounded question "What is this project's purpose and what is its primary programming language?" and keep the returned text verbatim for sharing. While that query runs, take responsibility in the infra-team channel under the message about Security flagged dependency 'belmont/cache by saying you will scan belmont/cache at v1.4.1 and produce a short summary covering license, primary programming language, and maintainer/contact by EOD. Post a follow-up in that same thread indicating you are starting the scan and will update the thread with the short summary when it’s ready. When the AI answer arrives, post it exactly as returned into the infra-team channel so the thread contains the verbatim result, reply in the original thread that the summary is posted and that you DM'd a copy to David, add a ':+1:' reaction to your starting-the-scan message, and send the AI’s answer verbatim to the conversation where Security pinged me about came up so David receives the same result.
```

## Warnings recorded for this task

- stage 5 dropped: chat n3: chat 'n3' names an undeclared member 'you'
- stage 5 dropped: message n13: message 'n13' is in undeclared chat 'n3'
- stage 5 dropped: message n15: message 'n15' is from undeclared sender 'you'
- stage 5 dropped: message n4: message 'n4' is from undeclared sender 'you'
- stage 5 dropped: message n5: message 'n5' is from undeclared sender 'you'
- stage 5 dropped: message n10: message 'n10' is from undeclared sender 'you'
- stage 5 dropped: message n11: message 'n11' is from undeclared sender 'you'
- stage 5 dropped: message n12: message 'n12' is from undeclared sender 'you'
- stage 5 dropped: message n14: message 'n14' is in undeclared chat 'n3'
- stage 5 dropped: message n16: message 'n16' is from undeclared sender 'you'
