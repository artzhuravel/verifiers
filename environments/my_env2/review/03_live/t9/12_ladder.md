# The ladder — t9

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
| `$user_0` | Devon Park @devon | `u_devon` | "whoever wrote the message about names and owners into" | 1/1/0 |
| `$message_0` | in docs-sync from Priya Singh, replying to m_001: 'Can someone c | `m_004` | "the message about someone collect the exact" | 1/1/0 |
| `$chat_0` | dm (unnamed dm) — members: Alex Rivera @you, Devon Park @devon | `c_002` | "the conversation where names and owners into came up" | 1/1/0 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Call get_user with user_id = u_devon to look up the user Devon Park and record the returned user object.
2. Call read_wiki_contents with repoName = 'facebook/react' and record the returned DeepWiki wiki documentation prose for that repository.
3. Call read_wiki_contents with repoName = 'kubernetes/kubernetes' and record the returned DeepWiki wiki documentation prose for that repository.
4. Reply to message m_004 in the docs-sync thread by posting a reply (use reply_to with message_id = m_004) whose message text includes the user information returned for u_devon from step 1 and also includes the wiki documentation prose returned for 'kubernetes/kubernetes' from step 3.
5. Send a direct message to chat c_002 (use send_message with chat_id = c_002) whose message text includes the user information returned for u_devon from step 1.
6. Reply to message m_004 in the docs-sync thread by posting a reply (use reply_to with message_id = m_004) whose message text includes the wiki documentation prose returned for 'facebook/react' from step 2.
7. Call list_chats to get the list of chats the acting user is a member of, and include that list of chats in your final reply to me (report the array returned by list_chats in your response).
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: The reply posted in step 4 includes the user information returned for u_devon (identifying Devon Park, e.g., name and/or handle or id) and also includes the DeepWiki wiki documentation prose retrieved for the 'kubernetes/kubernetes' repository.
    - where to look: Look at the text of the reply message created by step 4 (the reply to m_004 in the docs-sync thread).
- **carry:c0a2:text**
    - a correct answer says: The direct message sent to chat c_002 in step 5 contains the user information returned for u_devon (identifying Devon Park, e.g., name and/or handle or id).
    - where to look: Look at the text of the message created by step 5 (the send_message to chat c_002).
- **carry:c1a1:text**
    - a correct answer says: The reply posted in step 6 includes the DeepWiki wiki documentation prose retrieved for the 'facebook/react' repository.
    - where to look: Look at the text of the reply message created by step 6 (the reply to m_004 in the docs-sync thread).
- **report:c1a2**
    - a correct answer says: The agent's final reply lists the chats returned by list_chats: c_001 (group, name 'docs-sync', members u_me, u_liam, u_sofia, u_priya), c_002 (dm, name 'c_002', members u_me, u_devon), and c_003 (group, name 'c_003', members u_me, u_liam, u_marcus).
    - where to look: Check the agent's final reply for the reported list_chats output.

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Look up whoever wrote the message about names and owners into to obtain their user object, then fetch the DeepWiki wiki documentation prose for the repositories 'facebook/react' and 'kubernetes/kubernetes'. After that, reply in-thread to the message about someone collect the exact by posting a reply whose text includes the user information you retrieved and the wiki documentation prose you fetched for 'kubernetes/kubernetes'. Send a direct message in the conversation where names and owners into came up containing the user information you retrieved. Then post another reply under that same message whose text includes the wiki documentation prose you fetched for 'facebook/react'. Finally, call list_chats to get the list of chats the acting user is a member of and include that list (the array returned by list_chats) in your final reply to me.
```

### What the judge checks at L2

- **carry:c0a1:text**
    - a correct answer says: The reply posted under the message about someone collect the exact includes the user information returned for whoever wrote the message about names and owners into (identifying that person, e.g., name and/or handle or id) and also includes the DeepWiki wiki documentation prose retrieved for the 'kubernetes/kubernetes' repository.
    - where to look: Look at the text of the reply message created by the reply to the message about someone collect the exact in the docs-sync thread.
- **carry:c0a2:text**
    - a correct answer says: The direct message sent in the conversation where names and owners into came up contains the user information returned for whoever wrote the message about names and owners into (identifying that person, e.g., name and/or handle or id).
    - where to look: Look at the text of the direct message posted in the conversation where names and owners into came up.
- **carry:c1a1:text**
    - a correct answer says: The reply posted under the message about someone collect the exact includes the DeepWiki wiki documentation prose retrieved for the 'facebook/react' repository.
    - where to look: Look at the text of the reply message created by the reply to the message about someone collect the exact in the docs-sync thread.
- **report:c1a2**
    - a correct answer says: The agent's final reply lists the chats returned by list_chats: the group whose name is 'docs-sync' with members Alex Rivera @you, Liam Chen @liam, Sofia Morales @sofia, and Priya Singh @priya; the direct-message conversation where names and owners into came up with members Alex Rivera @you and whoever wrote the message about names and owners into; and the group whose name is 'c_003' with members Alex Rivera @you, Liam Chen @liam, and Marcus Lee @marcus. The array structure and these entries should appear in the agent's final reply exactly as the list_chats output.
    - where to look: Check the agent's final reply for the reported list_chats output (the array the agent was asked to include).

## L3 — the goal. No step individually identifiable.

```text
Locate the user object for whoever wrote the message about names and owners into — the direct note in the DM that said a CSV of repo names and owners was placed at /team/docs/repo-list.csv. Fetch the DeepWiki wiki documentation prose for 'facebook/react' and 'kubernetes/kubernetes'. In the docs-sync thread, reply to the message about someone collect the exact — "Can someone collect the exact GitHub repo names and DeepWiki repo wikis for the plugins we listed? I need them to start reading. Please list them in this thread." — by posting a reply whose text contains the user information you retrieved and the wiki prose for 'kubernetes/kubernetes'. Send a direct message in the conversation where names and owners into came up — the DM that announced the CSV — containing the same user information. Post another reply under that same message about someone collect the exact whose text contains the wiki prose for 'facebook/react'. Finally, retrieve the list of chats the acting user belongs to and include the returned array exactly as the call returns in your final reply to me.
```

### What the judge checks at L3

- **carry:c0a1:text**
    - a correct answer says: The reply posted under the message about someone collect the exact includes the user information returned for whoever wrote the message about names and owners into (identifying that person, e.g., name and/or handle or id) and also includes the DeepWiki wiki documentation prose retrieved for the 'kubernetes/kubernetes' repository.
    - where to look: Look at the text of the reply message created by replying to the message about someone collect the exact in the docs-sync thread.
- **carry:c0a2:text**
    - a correct answer says: The direct message sent in the conversation where names and owners into came up contains the user information returned for whoever wrote the message about names and owners into (identifying that person, e.g., name and/or handle or id).
    - where to look: Look at the text of the direct message posted in the conversation where names and owners into came up.
- **carry:c1a1:text**
    - a correct answer says: The reply posted under the message about someone collect the exact includes the DeepWiki wiki documentation prose retrieved for the 'facebook/react' repository.
    - where to look: Look at the text of the reply message created by replying to the message about someone collect the exact in the docs-sync thread.
- **report:c1a2**
    - a correct answer says: The agent's final reply includes the array returned by the list_chats call: an entry for the group named 'docs-sync' with members Alex Rivera @you, Liam Chen @liam, Sofia Morales @sofia, and Priya Singh @priya; an entry for the direct-message conversation where names and owners into came up with members Alex Rivera @you and whoever wrote the message about names and owners into; and an entry for the group with members Alex Rivera @you, Liam Chen @liam, and Marcus Lee @marcus. The array structure and these entries should appear in the agent's final reply exactly as the list_chats output.
    - where to look: Check the agent's final reply for the reported array (the list_chats output) showing the docs-sync group, the direct-message conversation where names and owners into came up, and the other group with Alex Rivera @you, Liam Chen @liam, and Marcus Lee @marcus.

## L4 — folded. Actions that existed only to feed each other become one request, no content is dictated word for word, and no clause narrates a hand-off.

```text
Find the user object for the teammate who posted the DM announcing a CSV of repo names and owners at /team/docs/repo-list.csv. Fetch the DeepWiki wiki documentation prose for the repositories facebook/react and kubernetes/kubernetes. In the docs-sync thread, reply to the message that asks the team to collect the exact GitHub repo names and DeepWiki repo wikis for the plugins we listed with two separate replies: one reply should include the teammate's user information and the kubernetes/kubernetes wiki prose, and the other reply should include the facebook/react wiki prose. Also send a direct message to the teammate who announced the CSV that contains their user information. Finally, call the API that lists the chats I belong to and include the exact array that call returns in your final reply to me.
```

### What the judge checks at L4

- **carry:c0a1:text**
    - a correct answer says: The reply posted under the message asking the team to collect the exact GitHub repo names and DeepWiki repo wikis contains the user information for the teammate who posted the DM announcing the CSV of repo names and owners at /team/docs/repo-list.csv, and it also contains the DeepWiki wiki documentation prose retrieved for the 'kubernetes/kubernetes' repository.
    - where to look: Look at the text of the reply message created by replying to the message that asks the team to collect the exact GitHub repo names and DeepWiki repo wikis in the docs-sync thread; that reply should show the teammate's user information and the 'kubernetes/kubernetes' wiki prose.
- **carry:c0a2:text**
    - a correct answer says: The direct message sent in the DM where the CSV of repo names and owners was announced contains the user information for the teammate who announced that CSV.
    - where to look: Look at the text of the direct message posted in the DM that announced the CSV of repo names and owners; it should include the teammate's user information.
- **carry:c1a1:text**
    - a correct answer says: The second reply posted under the message asking the team to collect the exact GitHub repo names and DeepWiki repo wikis contains the DeepWiki wiki documentation prose retrieved for the 'facebook/react' repository.
    - where to look: Look at the text of the other reply message created by replying to the message that asks the team to collect the exact GitHub repo names and DeepWiki repo wikis in the docs-sync thread; that reply should show the 'facebook/react' wiki prose.
- **report:c1a2**
    - a correct answer says: The agent's final reply includes the exact array returned by the call that lists the chats the acting user belongs to: an entry for the group named 'docs-sync' with members Alex Rivera @you, Liam Chen @liam, Sofia Morales @sofia, and Priya Singh @priya; an entry for the direct-message conversation where the CSV was announced with members Alex Rivera @you and the teammate who announced the CSV; and an entry for the other group with members Alex Rivera @you, Liam Chen @liam, and Marcus Lee @marcus. The array structure and these entries should appear exactly as the list-of-chats output.
    - where to look: Check the agent's final reply for the reported array (the list-of-chats output) showing the docs-sync group, the direct-message conversation where the CSV was announced, and the other group with Alex Rivera @you, Liam Chen @liam, and Marcus Lee @marcus.

## Warnings recorded for this task

- stage 5 dropped: message n3: message 'n3' is from 'u2', who is not in 'c1'
- stage 5 dropped: message n5: message 'n5' is from 'u1', who is not in 'c2'
- v2: named 'list_chats'
- v2: judge item report:c1a2: still names 'c_003'
- v2: judge item report:c1a2: still names 'list_chats'
- v3: judge item report:c1a2: still names 'list_chats'
