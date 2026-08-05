# The ladder — t5

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
| `$message_0` | in infra from Tom Rivera, unread by you: "Can someone run DeepWi | `m_001` | "the message about someone run DeepWiki to" | 2/1/0 |
| `$message_1` | in docs from Lina Wong, unread by you: 'Heads-up: I also want th | `m_002` | "the message about doc-topic list for acme/monitoring" | 2/1/0 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Run read_wiki_structure with repoName 'acme/edge-proxy' and record the returned list of DeepWiki documentation topic titles for acme/edge-proxy for use in step 4.  2. Run list_chats to list the chats the acting user (u_me) is a member of and record the returned array of chat objects (id, kind, name, members) for use in steps 4 and 6.  3. Reply to message m_001 in chat c_001 with the text: 'On it — running DeepWiki for acme/edge-proxy now. I’ll paste the topic list here and into #docs.'  4. Reply to message m_002 in chat c_002 with a message that includes (a) the full list_chats result you obtained in step 2 (each chat's id, kind, name, and members) and (b) the list of DeepWiki documentation topic titles you obtained in step 1, and post that combined information as the reply body.  5. Add the ':+1:' reaction to the message you created in step 4.  6. Reply to message m_001 in chat c_001 with a message that includes the full list_chats result you obtained in step 2 (each chat's id, kind, name, and members) in the reply body.
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: The reply to m_002 states the three chats returned by list_chats with their ids, kinds, names, and member lists (infra c_001 with members u_me, u_mpatel, u_trivera, u_abrooks; docs c_002 with members u_me, u_mpatel, u_lwong; random c_003 with members u_me, u_mpatel, u_dramos) and it also includes the DeepWiki documentation topic titles returned for acme/edge-proxy.
    - where to look: Look in the reply message posted to m_002 (the message created in step 4).
- **carry:c1a1:text**
    - a correct answer says: The reply to m_001 includes the full list_chats result showing the three chats with their ids, kinds, names, and member lists (infra c_001 with members u_me, u_mpatel, u_trivera, u_abrooks; docs c_002 with members u_me, u_mpatel, u_lwong; random c_003 with members u_me, u_mpatel, u_dramos).
    - where to look: Look in the reply message posted to m_001 created in step 6.

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
You are Sam Ortega acting in the chat workspace. First, run DeepWiki for the repository acme/edge-proxy to obtain the list of documentation topic titles for that repo. Also list the chats that the acting user is a member of; that listing will return the array of group chats the user belongs to (the three groups are the one named "infra" whose members are Sam Ortega, Maya Patel, Tom Rivera, and Aaron Brooks; the one named "docs" whose members are Sam Ortega, Maya Patel, and Lina Wong; and the one named "random" whose members are Sam Ortega, Maya Patel, and Diego Ramos). After you have both results, reply in-thread to the message about someone run DeepWiki to with the exact text: 'On it — running DeepWiki for acme/edge-proxy now. I’ll paste the topic list here and into #docs.' Next, reply in-thread to the message about doc-topic list for acme/monitoring with a message whose body includes both the full chat-listing result you obtained (showing each chat's id, kind, name, and member list) and the list of DeepWiki documentation topic titles you obtained for acme/edge-proxy. After posting that reply to the message about doc-topic list for acme/monitoring, add the ':+1:' reaction to the reply you just created. Finally, post another reply in-thread to the message about someone run DeepWiki to that includes the full chat-listing result you obtained (each chat's id, kind, name, and members) in the reply body.
```

### What the judge checks at L2

- **carry:c0a1:text**
    - a correct answer says: The reply posted to the message about doc-topic list for acme/monitoring contains the three group chats returned by the chat-listing action with their ids, kinds, names, and member lists (the group named "infra" with members Sam Ortega, Maya Patel, Tom Rivera, and Aaron Brooks; the group named "docs" with members Sam Ortega, Maya Patel, and Lina Wong; the group named "random" with members Sam Ortega, Maya Patel, and Diego Ramos) and it also includes the DeepWiki documentation topic titles returned for acme/edge-proxy.
    - where to look: Look in the reply message you posted to the message about doc-topic list for acme/monitoring (the message created when you carried the combined information).
- **carry:c1a1:text**
    - a correct answer says: The reply posted to the message about someone run DeepWiki to includes the full chat-listing result showing the three chats with their ids, kinds, names, and member lists (the group named "infra" with members Sam Ortega, Maya Patel, Tom Rivera, and Aaron Brooks; the group named "docs" with members Sam Ortega, Maya Patel, and Lina Wong; the group named "random" with members Sam Ortega, Maya Patel, and Diego Ramos).
    - where to look: Look in the reply message you posted to the message about someone run DeepWiki to that you created at the end of the task.

## L3 — the goal. No step individually identifiable.

```text
You are Sam Ortega in the workspace. Run DeepWiki for the repository acme/edge-proxy to collect the repository's documentation topic titles, and retrieve the list of chats you belong to; that chat listing will show three group chats: the group named "infra" (members: Sam Ortega, Maya Patel, Tom Rivera, Aaron Brooks), the group named "docs" (members: Sam Ortega, Maya Patel, Lina Wong), and the group named "random" (members: Sam Ortega, Maya Patel, Diego Ramos). Once you have both results, post a threaded reply to the message about someone run DeepWiki to confirming you are running DeepWiki and that you will paste the topic list here and into #docs. Post a threaded reply to the message about doc-topic list for acme/monitoring whose body includes the complete chat-listing output (each chat's id, kind, name, and full member lists) together with the documentation topic titles you obtained for acme/edge-proxy. Add a ':+1:' reaction to that reply. Finally, post another threaded reply to that original message about someone run DeepWiki to whose body contains the full chat-listing output (each chat's id, kind, name, and members).
```

### What the judge checks at L3

- **carry:c0a1:text**
    - a correct answer says: The reply posted to the message about doc-topic list for acme/monitoring contains the three group chats returned by the chat-listing action with their ids, kinds, names, and member lists (the group named "infra" with members Sam Ortega, Maya Patel, Tom Rivera, and Aaron Brooks; the group named "docs" with members Sam Ortega, Maya Patel, and Lina Wong; and the group named "random" with members Sam Ortega, Maya Patel, and Diego Ramos) and it also includes the DeepWiki documentation topic titles returned for acme/edge-proxy.
    - where to look: Look in the reply message you posted to the message about doc-topic list for acme/monitoring (the message created when you carried the combined information).
- **carry:c1a1:text**
    - a correct answer says: The reply posted to the message about someone run DeepWiki to includes the full chat-listing result showing the three chats with their ids, kinds, names, and member lists (the group named "infra" with members Sam Ortega, Maya Patel, Tom Rivera, and Aaron Brooks; the group named "docs" with members Sam Ortega, Maya Patel, and Lina Wong; and the group named "random" with members Sam Ortega, Maya Patel, and Diego Ramos).
    - where to look: Look in the reply message you posted to the message about someone run DeepWiki to that you created at the end of the task.

## L4 — folded. Actions that existed only to feed each other become one request, no content is dictated word for word, and no clause narrates a hand-off.

```text
You are Sam Ortega. Get the DeepWiki documentation topic titles for the GitHub repo acme/edge-proxy, and get the list of group chats you belong to. Then do the following in the workspace: 

1) In the thread where someone asked for someone to run DeepWiki, post a reply confirming you will run DeepWiki for acme/edge-proxy and that you will paste the topic list into that thread and into the docs channel. Refer to that conversation as that thread after this.

2) In the thread where someone asked for the doc-topic list for acme/monitoring, post a reply that includes the complete chat-listing output (each chat's id, kind, name, and full member lists) together with the DeepWiki documentation topic titles you obtained for acme/edge-proxy. Call that conversation that thread for the doc-topic request.

3) Add a :+1: reaction to the reply you post in the doc-topic-request thread.

4) Finally, post another reply in the first thread (the one asking someone to run DeepWiki) that contains the complete chat-listing output (each chat's id, kind, name, and full member lists).
```

### What the judge checks at L4

- **carry:c0a1:text**
    - a correct answer says: The reply posted in the thread requesting the doc-topic list for acme/monitoring includes the full chat-listing output showing the three group chats with their ids, kinds, names, and complete member lists (the group named "infra" with members Sam Ortega, Maya Patel, Tom Rivera, and Aaron Brooks; the group named "docs" with members Sam Ortega, Maya Patel, and Lina Wong; and the group named "random" with members Sam Ortega, Maya Patel, and Diego Ramos) and it also includes the DeepWiki documentation topic titles returned for acme/edge-proxy.
    - where to look: Check the reply you posted in the thread that asked for the doc-topic list for acme/monitoring — the message you created that combines the chat list and the DeepWiki topic titles.
- **carry:c1a1:text**
    - a correct answer says: The reply posted in the thread that asked someone to run DeepWiki contains the full chat-listing result showing the three group chats with their ids, kinds, names, and complete member lists (the group named "infra" with members Sam Ortega, Maya Patel, Tom Rivera, and Aaron Brooks; the group named "docs" with members Sam Ortega, Maya Patel, and Lina Wong; and the group named "random" with members Sam Ortega, Maya Patel, and Diego Ramos).
    - where to look: Look at the final reply you posted in the thread where someone asked for someone to run DeepWiki — that message should include the complete chat-listing output.

## Warnings recorded for this task

- v2: pasted the description 'the message about someone run DeepWiki to' 2 times; introduce a thing once, then refer back to it
- v2: pasted the description 'the message about doc-topic list for acme/monitoring' 2 times; introduce a thing once, then refer back to it
- v3: 1 sequencing connective(s) — reads as a list in prose clothing
- v4: still enumerates 4 step(s)
- v4: 1 sequencing connective(s) — reads as a list in prose clothing
