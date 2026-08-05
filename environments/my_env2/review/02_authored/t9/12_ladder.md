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
| `$user_0` | Lina Park @lina_p | `u_lina_p` | "the person whose handle is @lina_p" | 1/1 |
| `$message_0` | in backend-architecture from Jamal Reed, unread by you: "Lina —  | `m_004` | "the message about confirm which GitHub repo" | 2/2 |
| `$chat_0` | group 'oncall' — members: You @you, Marco Silva @marco_s, Priya  | `c_002` | "the oncall channel" | 1/1 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Call get_user with user_id = u_lina_p to look up Lina Park and save the returned user object.
2. Call read_wiki_contents with repoName = 'prometheus/node_exporter' and save the returned wiki documentation prose for that repo.
3. Call read_wiki_contents with repoName = 'prometheus/prometheus' and save the returned wiki documentation prose for that repo.
4. Reply to message m_004 (in chat c_001, backend-architecture) with a threaded reply that includes the user lookup result from step 1 and the wiki documentation prose returned in step 3; the reply should address Jamal's question about which GitHub repo to cite and who the primary contact is, and must contain the actual values returned by steps 1 and 3.
5. Send a message to chat c_002 (oncall) that includes the user lookup result from step 1; the message must contain the actual value returned by step 1.
6. Reply to message m_004 (in chat c_001, backend-architecture) with a threaded reply that includes the wiki documentation prose returned in step 2; the reply must contain the actual value returned by step 2.
7. Call list_chats to retrieve the chats the acting user is a member of, and include the full returned array of chats in your final (agent) reply after performing the writes above.
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: The reply posted to message m_004 names Lina Park and her handle (showing the user object for u_lina_p, name 'Lina Park', handle '@lina_p') and also includes the DeepWiki documentation prose for the 'prometheus/prometheus' repository (a descriptive passage from that repo's wiki explaining the project or a subsystem).
    - where to look: Look at the body of the threaded reply created by step 4 (the reply to m_004).
- **carry:c0a2:text**
    - a correct answer says: The message sent to chat c_002 contains the user lookup result for Lina Park, i.e. the user details for u_lina_p including her name 'Lina Park' and handle '@lina_p'.
    - where to look: Look at the message body posted to chat c_002 in step 5.
- **carry:c1a1:text**
    - a correct answer says: The reply posted to message m_004 includes the DeepWiki documentation prose for 'prometheus/node_exporter' — a descriptive excerpt or the full prose from that repository's wiki explaining the project or subsystem behavior.
    - where to look: Check the body of the second threaded reply to m_004 created in step 6.
- **report:c1a2**
    - a correct answer says: The agent reports the list of chats: c_001 (group, name 'backend-architecture') with members [u_me, u_marco_s, u_lina_p, u_jamal_r]; c_002 (group, name 'oncall') with members [u_me, u_marco_s, u_priya_d]; and c_003 (group, name 'c_003') with members [u_me, u_marco_s, u_carlos_v].
    - where to look: Look in the agent's final reply (the summary it returns after performing the actions) for the list_chats result.

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Please look up the person whose handle is @lina_p and save the returned user object, then view the DeepWiki documentation prose for 'prometheus/node_exporter' and for 'prometheus/prometheus' and save each returned prose. After that, reply in-thread to the message about confirm which GitHub repo with a reply that includes the saved user object and the 'prometheus/prometheus' documentation prose, addressing Jamal's question about which GitHub repo to cite and who the primary contact is and including the actual values returned by the user lookup and that wiki read. Next, send a message to the oncall channel that includes the saved user object and contains the actual value returned by the user lookup. Then post another in-thread reply to the message about confirm which GitHub repo that includes the 'prometheus/node_exporter' documentation prose and contains the actual value returned by that wiki read. Finally, retrieve the chats the acting user is a member of and include the full returned array of chats in your final reply here after performing the writes above; report back in this thread with those results.
```

## L3 — the goal. No step individually identifiable.

```text
Produce and publish the concrete artifacts the team needs: obtain the user object for the person whose handle is @lina_p and fetch the DeepWiki prose for 'prometheus/node_exporter' and 'prometheus/prometheus', then use those actual returned values in the appropriate communications so the work is actionable — post a threaded reply to the message about confirm which GitHub repo that includes the full user object and the actual 'prometheus/prometheus' prose so the question about which GitHub repo to cite and who the primary contact is is directly answered, send a message to the oncall channel that includes the full user object, post a threaded reply to the message about confirm which GitHub repo that includes the actual 'prometheus/node_exporter' prose, and after making those posts retrieve the list of chats the acting user is a member of and include the complete returned array of chats in your final reply here.
```

## Warnings recorded for this task

(none)
