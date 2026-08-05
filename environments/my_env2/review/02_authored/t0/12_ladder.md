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
| `$message_0` | in backend-sprint from Ben Carter, replying to m_001, unread by  | `m_002` | "the reply to the message about audit the payment integration" | 2/2 |
| `$chat_0` | dm (unnamed dm) — members: Sam Li @you, Carla Ruiz @carla | `c_002` | "the conversation where DeepWiki about owner/billing to came up" | 2/2 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Run an ask_question on DeepWiki for repoName='stripe/stripe-go' with the question: "What's the repository's license and primary programming language?" and keep the returned answer available for the next steps. 2. Reply to message m_002 in chat c_001 with the text: "On it — I'm checking stripe/stripe-go on DeepWiki for the repo license and primary language; will post results here." 3. Send a DM in chat c_002 (to Carla) with the text: "Per your request, I asked DeepWiki about stripe/stripe-go (repo: stripe/stripe-go). I'll send license and language as soon as I get it so you can forward to Legal." 4. Reply to message m_002 in chat c_001 with a message that states, in a concise sentence, the repository license and the primary programming language returned by the DeepWiki query you ran in step 1 (for example: "stripe/stripe-go is licensed under <LICENSE> and is primarily written in <LANGUAGE>."); do not paste the full DeepWiki output but restate the license and language in your own words. 5. Reply to the message you sent in step 3 with the text: "Got it — I'll forward the license and language to Legal once the DeepWiki answer comes back." 6. Add the ':+1:' reaction to the message you posted in step 4.
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: A concise sentence stating that stripe/stripe-go is licensed under the MIT License and that its primary programming language is Go.
    - where to look: Check the reply to m_002 that the agent posts in step 4; the sentence there should state the repo license and the primary programming language.

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Please query DeepWiki about the repository stripe/stripe-go by asking exactly "What's the repository's license and primary programming language?" and keep the returned answer available for the following actions. Next, reply in-thread to the reply to the message about audit the payment integration with the text: "On it — I'm checking stripe/stripe-go on DeepWiki for the repo license and primary language; will post results here." Then send a direct message in the conversation where DeepWiki about owner/billing to came up to Carla with the text: "Per your request, I asked DeepWiki about stripe/stripe-go (repo: stripe/stripe-go). I'll send license and language as soon as I get it so you can forward to Legal." When the DeepWiki answer is available, reply in-thread to the reply to the message about audit the payment integration with a concise sentence that states the repository license and the primary programming language returned by that query, for example "stripe/stripe-go is licensed under <LICENSE> and is primarily written in <LANGUAGE>.", restating the license and language in your own words rather than pasting the full DeepWiki output. After that, reply to the message you sent in the conversation where DeepWiki about owner/billing to came up with the text: "Got it — I'll forward the license and language to Legal once the DeepWiki answer comes back." Finally add the ':+1:' reaction to the message where you reported the license and primary language in-thread.
```

## L3 — the goal. No step individually identifiable.

```text
Get the repository license and primary programming language for stripe/stripe-go by asking DeepWiki exactly "What's the repository's license and primary programming language?" and keep that answer available for follow-up. While that query is pending, reply in-thread to the reply to the message about audit the payment integration to say you are checking stripe/stripe-go on DeepWiki for the repo license and primary language and will post the results here. Also message Carla in the conversation where DeepWiki about owner/billing to came up to let her know you asked DeepWiki about stripe/stripe-go and that you will send license and language details for Legal as soon as they arrive. When the DeepWiki answer is available, post a concise in-thread reply to the reply to the message about audit the payment integration restating the repository license and the primary programming language in your own words in a single short sentence that names stripe/stripe-go and identifies the license and language. After that, reply to the message you sent in the conversation where DeepWiki about owner/billing to came up to confirm you will forward the license and language to Legal once the DeepWiki answer comes back. Finally add a ":+1:" reaction to the in-thread message where you reported the license and primary language.
```

## Warnings recorded for this task

- stage 5 dropped: chat n2: chat 'n2' names an undeclared member 'you'
- stage 5 dropped: message n8: message 'n8' is in undeclared chat 'n2'
- stage 5 dropped: message n9: message 'n9' is from undeclared sender 'you'
- stage 5 dropped: message n10: message 'n10' replies to 'n9', which is not an earlier message
