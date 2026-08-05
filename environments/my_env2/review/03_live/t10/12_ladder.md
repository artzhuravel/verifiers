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
| `$chat_0` | group 'product-team' — members: You @you, Maya Singh @maya_r, Lu | `c_001` | "the product-team channel" | 2/2/4 |
| `$message_0` | in c_002 from Maya Singh, unread by you: "Can you paste the full | `m_004` | "the message about paste the full list" | 1/1/0 |
| `$message_1` | in product-team from Priya Kapoor, unread by you: "Could someone | `m_009` | "the message about Could someone check acme/cli-helper" | 1/1/0 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Call list_chats and record the array it returns (each chat object with id, kind, name, and members).
2. Send a message to chat c_001 with the text: "On it — I'll check acme/cli-helper on DeepWiki for the license and primary language and paste the excerpt here shortly; assembling the release notes tonight."
3. Call ask_question with repoName 'aws/aws-cli' and question "What is this repository's license and primary programming language?" and save the free-text answer.
4. Call mark_read for chat c_001 to mark every message there as read by you.
5. Reply to the message you created in step 2 (use that message's id) in its chat with the text: "Following up — I'll paste the DeepWiki excerpt into this thread as soon as I have it."
6. Reply to message m_004 in chat c_002 with a message that includes the full list of your current chats: for each chat include its id, kind, name, and the member ids exactly as returned by your list_chats result from step 1.
7. Reply to message m_009 in chat c_001 with a message that includes the answer text you received from the ask_question call in step 3, explicitly stating the repository's license and its primary programming language.
```

### What the judge checks at L1

- **carry:c1a2:text**
    - a correct answer says: The reply to m_004 lists three chats exactly: c_001 (kind: group, name: "product-team", members: u_me, u_maya_r, u_luis_h, u_priya_k, u_ben_z), c_002 (kind: dm, name: "c_002", members: u_me, u_maya_r), and c_003 (kind: group, name: "c_003", members: u_me, u_maya_r, u_evelyn_c).
    - where to look: Look in the message posted in step 6—the reply to m_004 in chat c_002.
- **carry:c0a2:text**
    - a correct answer says: The reply to m_009 states that the aws/aws-cli repository uses the Apache-2.0 license and that its primary programming language is Python.
    - where to look: Look in the message posted in step 7—the reply to m_009 in chat c_001, which should include the ask_question answer about aws/aws-cli.

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Retrieve the array returned when you list the chats the acting user is a member of and record it, where each chat object includes its id, kind, name, and members. Post this message to the product-team channel: "On it — I'll check acme/cli-helper on DeepWiki for the license and primary language and paste the excerpt here shortly; assembling the release notes tonight." Then ask about the GitHub repository aws/aws-cli with the exact question "What is this repository's license and primary programming language?" and save the free-text answer you receive. After that, mark every message in that channel as read by the acting user. Reply in that channel to the message you just posted with: "Following up — I'll paste the DeepWiki excerpt into this thread as soon as I have it." Reply to the message about paste the full list (the message in the DM with Maya Singh asking for the full list of current chats) with a message that includes the full array you recorded when you listed your chats, showing for each chat its id, kind, name, and members exactly as returned. Finally, reply to the message about Could someone check acme/cli-helper in the product-team channel with a message that includes the answer text you received when you asked about aws/aws-cli, explicitly stating the repository's license and its primary programming language.
```

### What the judge checks at L2

- **carry:c1a2:text**
    - a correct answer says: The reply to the message about paste the full list lists three chats exactly: the product-team channel (kind: group, name: "product-team", members: You, Maya Singh, Luis Hernández, Priya Kapoor, Ben Zhao), the direct message between You and Maya Singh (kind: dm, name and id as returned by the system for that DM, members: You, Maya Singh), and the group that includes You, Maya Singh, and Evelyn Cho (kind: group, name and id as returned by the system for that group, members: You, Maya Singh, Evelyn Cho).
    - where to look: Look in the reply you posted to the message about paste the full list, the DM with Maya Singh.
- **carry:c0a2:text**
    - a correct answer says: The reply to the message about Could someone check acme/cli-helper states that the aws/aws-cli repository uses the Apache-2.0 license and that its primary programming language is Python.
    - where to look: Look in the reply you posted to the message about Could someone check acme/cli-helper in the product-team channel; it should include the answer you got about aws/aws-cli.

## L3 — the goal. No step individually identifiable.

```text
Collect and keep the exact array returned when you list the chats the acting user belongs to; every chat object must show its id, kind, name, and members. Post a message into the product-team channel to say you will check acme/cli-helper on DeepWiki for the license and primary language and will paste the excerpt there shortly; mention you will assemble the release notes tonight. Ask about the GitHub repository aws/aws-cli using the exact question "What is this repository's license and primary programming language?" and save the free-text answer you receive. Mark every message in that channel as read by the acting user. In that same channel, reply to the message you just posted with a short follow-up that says you will paste the DeepWiki excerpt into the thread as soon as you have it. Reply to the message about paste the full list in the DM with Maya Singh by posting the full array you recorded when you listed your chats, showing for each chat its id, kind, name, and members exactly as returned. Reply to the message about Could someone check acme/cli-helper in the product-team channel with the answer text you received about aws/aws-cli, explicitly stating the repository's license and its primary programming language.
```

### What the judge checks at L3

- **carry:c1a2:text**
    - a correct answer says: The reply to the message about paste the full list must present the three chats exactly as returned by the system: the product-team channel (kind: group, name: "product-team", members: You, Maya Singh, Luis Hernández, Priya Kapoor, Ben Zhao), the direct message between You and Maya Singh (kind: dm, with the name and id exactly as returned for that DM, members: You, Maya Singh), and the group that includes You, Maya Singh, and Evelyn Cho (kind: group, with the name and id exactly as returned for that group, members: You, Maya Singh, Evelyn Cho).
    - where to look: Look in the reply you posted to the message about paste the full list (the DM with Maya Singh).
- **carry:c0a2:text**
    - a correct answer says: The reply to the message about Could someone check acme/cli-helper must state that the aws/aws-cli repository uses the Apache-2.0 license and that its primary programming language is Python.
    - where to look: Look in the reply you posted to the message about Could someone check acme/cli-helper in the product-team channel; it should include the answer you received about aws/aws-cli.

## L4 — folded. Actions that existed only to feed each other become one request, no content is dictated word for word, and no clause narrates a hand-off.

```text
You are acting as the user in this environment. Do the following tasks in any convenient order but make sure each outcome happens:

- Retrieve the exact list of chats you belong to. For each chat record the id, kind, name, and full members list exactly as returned.
- In the product-team channel, post a message telling the team you will check the DeepWiki entry for the GitHub repository aws/aws-cli to find its license and primary programming language, and that you will paste the excerpt there shortly; also mention you will assemble the release notes tonight.
- Use the repo Q&A service to ask about the GitHub repository aws/aws-cli and get its license and its primary programming language (the repository name must be aws/aws-cli exactly).
- Mark every message in the product-team channel as read by you.
- In the product-team channel, reply in-thread to the message you posted there with a short follow-up saying you will paste the DeepWiki excerpt into the thread as soon as you have it.
- In the direct message from Maya that asks for the full list of current chats, reply by pasting the exact array you recorded when you retrieved your chats, showing for each chat object its id, kind, name, and members exactly as returned.
- In the product-team channel, reply to Priya’s message asking someone to check acme/cli-helper by posting the answer you received about aws/aws-cli, explicitly stating that repository’s license and its primary programming language.

Make sure the posted replies contain the exact data returned by the system for the chat list and the exact license and language information returned for aws/aws-cli; do not paraphrase those returned values.
```

### What the judge checks at L4

- **carry:c1a2:text**
    - a correct answer says: The reply posted in the DM to Maya’s request for the full list must contain the exact array that was returned when you retrieved your chats; each chat object in that array must include its id, its kind, its name, and its members. The three chats must appear exactly as returned: the product-team group (kind: group, name: "product-team", members: You, Maya Singh, Luis Hernández, Priya Kapoor, Ben Zhao), the direct message with Maya (kind: dm, with the name and id exactly as returned for that DM, members: You, Maya Singh), and the group that includes You, Maya Singh, and Evelyn Cho (kind: group, with the name and id exactly as returned for that group, members: You, Maya Singh, Evelyn Cho).
    - where to look: Look at the message you posted in reply to Maya’s DM asking for the full list; the exact chat-array you pasted there is what to check.
- **carry:c0a2:text**
    - a correct answer says: The reply posted in the product-team channel responding to Priya’s request about acme/cli-helper must state that the aws/aws-cli repository uses the Apache-2.0 license and that its primary programming language is Python.
    - where to look: Look at the reply you posted in the product-team channel to Priya’s message asking someone to check acme/cli-helper; it should include the aws/aws-cli license and primary language information.

## Warnings recorded for this task

- v2: pasted the description 'the product-team channel' 2 times; introduce a thing once, then refer back to it
- v3: pasted the description 'the product-team channel' 2 times; introduce a thing once, then refer back to it
- v3: 2 sequencing connective(s) — reads as a list in prose clothing
- v4: pasted the description 'the product-team channel' 4 times; introduce a thing once, then refer back to it
- v4: still enumerates 7 step(s)
- v4: 2 sequencing connective(s) — reads as a list in prose clothing
