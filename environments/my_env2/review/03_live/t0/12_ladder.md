# The ladder — t0

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
| `$message_0` | in infra from Maya Patel, unread by you: "Can someone confirm wh | `m_001` | "the message about someone confirm whether signalapp/libsignal-client" | 2/1/0 |
| `$chat_0` | group 'eng-team' — members: You @you, Maya Patel @maya, Ben Orti | `c_002` | "the eng-team channel" | 2/1/2 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Ask the ask_question tool about the GitHub repository 'signalapp/libsignal-client' with the question: "What license is this repository released under, and does signalapp provide any official Rust bindings or Rust crate for it?".
2. Reply to message m_001 in chat c_001 (Maya Patel's infra thread) with the text: "On it — I'm running a quick repo check for license and any official Rust bindings and will post the findings here shortly.".
3. Send a message to chat c_002 (eng-team) with the text: "I'm checking signalapp/libsignal-client for license and any official Rust bindings and will post the results in the infra thread; Ben, can you double-check the license when I share it?".
4. Reply to message m_001 in chat c_001 with a message that carries the full answer you received from the ask_question call: include the repository's license name and explicitly state whether signalapp provides any official Rust bindings or a Rust crate (i.e., put the license and the bindings/crate conclusion returned by the repo query into this reply message text).
5. Reply to the message you created in step 3 (the eng-team message you just sent) with the text: "Done — I posted the license and Rust bindings info in the infra thread (reply to Maya). Please review and comment.".
6. Add the ':+1:' reaction to the message you created in step 4.
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: The reply to m_001 states the repository's license by name and explicitly says whether signalapp provides any official Rust bindings or a Rust crate (naming the crate if one exists, or stating that no official Rust bindings/crate are provided).
    - where to look: Look at the text of the message the agent posts in reply to m_001 in step 4; the reply should contain the license name and the bindings/crate conclusion.

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Query the repository 'signalapp/libsignal-client' with the question "What license is this repository released under, and does signalapp provide any official Rust bindings or Rust crate for it?" and capture the full response. Post a reply to the message about someone confirm whether signalapp/libsignal-client that says "On it — I'm running a quick repo check for license and any official Rust bindings and will post the findings here shortly." Then send a message to the eng-team channel that says "I'm checking signalapp/libsignal-client for license and any official Rust bindings and will post the results in the infra thread; Ben, can you double-check the license when I share it?" When you have the response to the repository query, post that response as a reply to the message about someone confirm whether signalapp/libsignal-client; that reply must state the repository's license by name and explicitly say whether signalapp provides any official Rust bindings or a Rust crate (naming the crate if one exists, or stating that no official Rust bindings/crate are provided). After posting that reply, reply to the message you sent to the eng-team channel with "Done — I posted the license and Rust bindings info in the infra thread (reply to Maya). Please review and comment." Finally, add a ':+1:' reaction to the reply that carries the repository answer.
```

### What the judge checks at L2

- **carry:c0a1:text**
    - a correct answer says: The reply to the message about someone confirm whether signalapp/libsignal-client states the repository's license by name and explicitly says whether signalapp provides any official Rust bindings or a Rust crate (naming the crate if one exists, or stating that no official Rust bindings/crate are provided).
    - where to look: Look at the text of the reply the agent posts to the message about someone confirm whether signalapp/libsignal-client; the reply should contain the license name and the bindings/crate conclusion.

## L3 — the goal. No step individually identifiable.

```text
Goal: determine whether signalapp/libsignal-client is acceptable to embed by identifying its license and whether the project provides any official Rust bindings or a Rust crate, then communicate the findings to the team and ask for a quick double-check. To get the facts, query the repository with the exact question 'What license is this repository released under, and does signalapp provide any official Rust bindings or Rust crate for it?' and record the full answer. Tell the group you're handling this by replying to the message about someone confirm whether signalapp/libsignal-client to say you're running a quick repo check and will post findings shortly, and also post into the eng-team channel that you're checking the repo for license and official Rust bindings, that you'll post results in the infra thread, and that Ben should double-check the license when you share it. When you receive the repository answer, post that answer as a reply to that message so the infra thread has the source material; that reply must name the repository's license and explicitly state whether signalapp provides official Rust bindings or a Rust crate (name the crate if one exists, or state that no official Rust bindings/crate are provided). After posting the answer, reply to your message in that channel to say you've posted the license and Rust bindings info in the infra thread and invite review, and add a :+1: reaction to the reply that contains the repository answer.
```

### What the judge checks at L3

- **carry:c0a1:text**
    - a correct answer says: The reply to the message about someone confirm whether signalapp/libsignal-client names the repository's license and explicitly states whether signalapp provides any official Rust bindings or an official Rust crate, naming that crate if it exists or stating that no official Rust bindings/crate are provided.
    - where to look: Examine the text of the reply the agent posts to the message about someone confirm whether signalapp/libsignal-client; that reply should include the license name and the conclusion about official Rust bindings/crate.

## L4 — folded. Actions that existed only to feed each other become one request, no content is dictated word for word, and no clause narrates a hand-off.

```text
You're acting as me in our chat workspace. Do these things for the signalapp/libsignal-client check:

1) In the infra thread where Maya asked whether signalapp/libsignal-client has Rust bindings and what its license is, reply to her now to say you’re running a quick repository check and will post the findings there shortly.

2) Query the GitHub repository signalapp/libsignal-client to determine two facts: the repository's license, and whether signalapp provides any official Rust bindings or an official Rust crate for this project. When you have the result, reply to Maya's message in that infra thread with the findings. That reply must name the license and explicitly state whether an official Rust bindings or Rust crate exists; if a crate exists, name it, otherwise state that none are provided.

3) In the eng-team channel, send a note saying you’re checking signalapp/libsignal-client for license and any official Rust bindings and that you’ll post the results in the infra thread; ask Ben to double-check the license when you share it.

4) After you post the repository findings into the infra thread, post a follow-up message in the eng-team channel saying you’ve posted the license and Rust bindings info in the infra thread and inviting review.

5) Add a thumbs-up (: +1:) reaction to the message you posted in the infra thread that contains the repository answer.
```

### What the judge checks at L4

- **carry:c0a1:text**
    - a correct answer says: The reply posted to Maya's question in the infra thread names the repository's license and explicitly states whether signalapp provides any official Rust bindings or an official Rust crate; if an official crate exists the reply names it, and if not the reply says that no official Rust bindings/crate are provided.
    - where to look: Look at the text of the reply the agent posts to Maya's message in the infra thread; it should include the license name and a clear conclusion about whether an official Rust bindings/crate exists (and the crate name if one does).

## Warnings recorded for this task

- v2: pasted the description 'the message about someone confirm whether signalapp/libsignal-client' 2 times; introduce a thing once, then refer back to it
- v2: pasted the description 'the eng-team channel' 2 times; introduce a thing once, then refer back to it
- v3: 2 sequencing connective(s) — reads as a list in prose clothing
- v4: pasted the description 'the eng-team channel' 2 times; introduce a thing once, then refer back to it
- v4: still enumerates 5 step(s)
- v4: 2 sequencing connective(s) — reads as a list in prose clothing
