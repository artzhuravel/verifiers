# The ladder — t2

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
| `$user_0` | Maya Singh @mg_singh | `u_mg_singh` | "whoever wrote the message about finalize the beta list" | 1/1/0 |
| `$user_1` | Carlos Rivera @crivera | `u_crivera` | "whoever wrote the message about worried about capacity for" | 1/1/0 |
| `$user_2` | Jen Park @jpark | `u_jpark` | "whoever wrote the message about final assets from design" | 1/1/0 |
| `$user_3` | Amir Qureshi @amirq | `u_amirq` | "whoever wrote the message about Pushed the revised hero" | 1/1/0 |
| `$chat_0` | group 'launch-team' — members: Alex Morgan @you, Maya Singh @mg_ | `c_001` | "the conversation where finalize the beta list came up" | 1/1/0 |
| `$message_0` | in launch-team from Carlos Rivera, unread by you: "I'm worried a | `m_005` | "the message about worried about capacity for" | 2/2/0 |
| `$message_1` | in design-queue from Amir Qureshi, unread by you: 'Pushed the re | `m_011` | "the message about Pushed the revised hero" | 2/2/0 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Run list_chats to list the chats the acting user (u_me) is a member of using the list_chats action. 2. Create a new group chat named 'beta-prioritization' that includes members u_mg_singh and u_crivera (the acting user is included automatically) by calling create_chat. 3. Create a new group chat named 'design-assets' that includes members u_jpark and u_amirq (the acting user is included automatically) by calling create_chat. 4. Send a message to chat c_001 (the group 'launch-team') by calling send_message; the message text must carry what list_chats returned in step 1, so look up the step 1 result and include in the message a concise summary that lists each returned chat's id, kind, name, and members. 5. Reply to message m_005 in its chat by calling reply_to; the reply text must carry what list_chats returned in step 1, so look up the step 1 result and include in the reply the same concise summary that lists each returned chat's id, kind, name, and members. 6. Reply to message m_011 in its chat by calling reply_to; the reply text must carry what list_chats returned in step 1, so look up the step 1 result and include in the reply the same concise summary that lists each returned chat's id, kind, name, and members.
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: The message in step 4 states that the acting user belongs to four chats: c_001 (group, named 'launch-team') with members u_me, u_mg_singh, u_crivera; c_002 (dm, named 'c_002') with members u_me, u_jpark; c_003 (group, named 'design-queue') with members u_me, u_amirq, u_mg_singh; and c_004 (group, named 'coffee-corner') with members u_me, u_mg_singh, u_spatel.
    - where to look: Look in the text of the message sent to chat c_001 (the send_message created in step 4).
- **carry:c1a1:text**
    - a correct answer says: The reply to m_005 in step 5 states that the acting user belongs to four chats: c_001 (group, named 'launch-team') with members u_me, u_mg_singh, u_crivera; c_002 (dm, named 'c_002') with members u_me, u_jpark; c_003 (group, named 'design-queue') with members u_me, u_amirq, u_mg_singh; and c_004 (group, named 'coffee-corner') with members u_me, u_mg_singh, u_spatel.
    - where to look: Look in the text of the reply created by replying to message m_005 (the reply_to in step 5).
- **carry:c0a2:text**
    - a correct answer says: The reply to m_011 in step 6 states that the acting user belongs to four chats: c_001 (group, named 'launch-team') with members u_me, u_mg_singh, u_crivera; c_002 (dm, named 'c_002') with members u_me, u_jpark; c_003 (group, named 'design-queue') with members u_me, u_amirq, u_mg_singh; and c_004 (group, named 'coffee-corner') with members u_me, u_mg_singh, u_spatel.
    - where to look: Look in the text of the reply created by replying to message m_011 (the reply_to in step 6).

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Please list the chats the acting user is a member of by running the read operation that enumerates chats. Then create a new group chat named 'beta-prioritization' that includes whoever wrote the message about finalize the beta list and whoever wrote the message about worried about capacity for (you are included automatically), and create another new group chat named 'design-assets' that includes whoever wrote the message about final assets from design and whoever wrote the message about Pushed the revised hero (you are included automatically). After that, post a concise summary of the chat-list result into the conversation where finalize the beta list came up, reply to the message about worried about capacity for with the same concise summary, and reply to the message about Pushed the revised hero with that same concise summary. Report back here with the two newly created chats and the three messages you posted.
```

### What the judge checks at L2

- **carry:c0a1:text**
    - a correct answer says: The message posted into the conversation where finalize the beta list came up states that the acting user belongs to four chats: a group conversation that is the conversation where finalize the beta list came up, whose members are the acting user, whoever wrote the message about finalize the beta list, and whoever wrote the message about worried about capacity for; a direct (one-on-one) conversation between the acting user and whoever wrote the message about final assets from design; a group conversation whose members are the acting user, whoever wrote the message about Pushed the revised hero, and whoever wrote the message about finalize the beta list; and a group conversation for casual breaks and random links whose members are the acting user, whoever wrote the message about finalize the beta list, and the person who started the casual chat for breaks and random links.
    - where to look: Look in the text of the message you posted into the conversation where finalize the beta list came up (the message sent into that conversation).
- **carry:c1a1:text**
    - a correct answer says: The reply made to the message about worried about capacity for states that the acting user belongs to four chats: a group conversation that is the conversation where finalize the beta list came up with members the acting user, whoever wrote the message about finalize the beta list, and whoever wrote the message about worried about capacity for; a direct (one-on-one) conversation between the acting user and whoever wrote the message about final assets from design; a group conversation whose members are the acting user, whoever wrote the message about Pushed the revised hero, and whoever wrote the message about finalize the beta list; and a group conversation for casual breaks and random links whose members are the acting user, whoever wrote the message about finalize the beta list, and the person who started the casual chat for breaks and random links.
    - where to look: Look in the text of the reply you posted in response to the message about worried about capacity for (the threaded reply to that message).
- **carry:c0a2:text**
    - a correct answer says: The reply made to the message about Pushed the revised hero states that the acting user belongs to four chats: a group conversation that is the conversation where finalize the beta list came up with members the acting user, whoever wrote the message about finalize the beta list, and whoever wrote the message about worried about capacity for; a direct (one-on-one) conversation between the acting user and whoever wrote the message about final assets from design; a group conversation whose members are the acting user, whoever wrote the message about Pushed the revised hero, and whoever wrote the message about finalize the beta list; and a group conversation for casual breaks and random links whose members are the acting user, whoever wrote the message about finalize the beta list, and the person who started the casual chat for breaks and random links.
    - where to look: Look in the text of the reply you posted in response to the message about Pushed the revised hero (the threaded reply to that message).

## L3 — the goal. No step individually identifiable.

```text
I need a short workflow completed: gather my current chat memberships and use that information to create two focused group spaces and broadcast the results into the relevant threads. First, identify the chats I belong to by enumerating my memberships. Create a group called 'beta-prioritization' that includes whoever wrote the message about finalize the beta list — the person who asked to finalize the beta candidate list by Friday — and whoever wrote the message about worried about capacity for — the person who raised capacity concerns for tier B. Create another group called 'design-assets' that includes whoever wrote the message about final assets from design — the person who asked if the final assets were ready — and whoever wrote the message about Pushed the revised hero — the person who posted the revised hero banner. Post a concise summary of the chat-list output into the conversation where finalize the beta list came up — the group thread where that request appears — and post that same concise summary as a threaded reply to the message about worried about capacity for — the capacity-concern message — and as a threaded reply to the message about Pushed the revised hero — the banner post. Return the two newly created group chats and the three messages you posted.
```

### What the judge checks at L3

- **carry:c0a1:text**
    - a correct answer says: The message posted into the conversation where finalize the beta list came up states that the acting user belongs to four chats: a group conversation that is the conversation where finalize the beta list came up whose members are the acting user, whoever wrote the message about finalize the beta list, and whoever wrote the message about worried about capacity for; a direct one-on-one conversation between the acting user and whoever wrote the message about final assets from design; a group conversation whose members are the acting user, whoever wrote the message about Pushed the revised hero, and whoever wrote the message about finalize the beta list; and a group conversation for casual breaks and random links whose members are the acting user, whoever wrote the message about finalize the beta list, and the person who started the casual chat for breaks and random links.
    - where to look: Look in the text of the message you posted into the conversation where finalize the beta list came up (the message sent into that conversation).
- **carry:c1a1:text**
    - a correct answer says: The reply made to the message about worried about capacity for states that the acting user belongs to four chats: a group conversation that is the conversation where finalize the beta list came up whose members are the acting user, whoever wrote the message about finalize the beta list, and whoever wrote the message about worried about capacity for; a direct one-on-one conversation between the acting user and whoever wrote the message about final assets from design; a group conversation whose members are the acting user, whoever wrote the message about Pushed the revised hero, and whoever wrote the message about finalize the beta list; and a group conversation for casual breaks and random links whose members are the acting user, whoever wrote the message about finalize the beta list, and the person who started the casual chat for breaks and random links.
    - where to look: Look in the text of the reply you posted in response to the message about worried about capacity for (the threaded reply to that message).
- **carry:c0a2:text**
    - a correct answer says: The reply made to the message about Pushed the revised hero states that the acting user belongs to four chats: a group conversation that is the conversation where finalize the beta list came up whose members are the acting user, whoever wrote the message about finalize the beta list, and whoever wrote the message about worried about capacity for; a direct one-on-one conversation between the acting user and whoever wrote the message about final assets from design; a group conversation whose members are the acting user, whoever wrote the message about Pushed the revised hero, and whoever wrote the message about finalize the beta list; and a group conversation for casual breaks and random links whose members are the acting user, whoever wrote the message about finalize the beta list, and the person who started the casual chat for breaks and random links.
    - where to look: Look in the text of the reply you posted in response to the message about Pushed the revised hero (the threaded reply to that message).

## L4 — folded. Actions that existed only to feed each other become one request, no content is dictated word for word, and no clause narrates a hand-off.

```text
Please run this short workflow as me.

1) Enumerate the chats I belong to.
2) Make a new group called 'beta-prioritization' and include the person who asked to finalize the beta candidate list by Friday and the person who raised the capacity concern for tier B.
3) Make another new group called 'design-assets' and include the person who asked whether the final design assets were ready and the person who posted the revised hero banner.
4) Post a concise summary of which chats I belong to into the group where the finalize-the-beta-list request was posted, and also post that exact concise summary as threaded replies to (a) the message that raised the tier-B capacity concern and (b) the message that posted the revised hero banner.

The concise summary should state that I belong to four chats: (a) the group where the finalize-the-beta-list request appears, whose members are me, the author of the finalize-the-beta-list message, and the author of the capacity-concern message; (b) a one-on-one DM between me and the author of the final-assets question; (c) a group whose members are me, the author of the revised-hero post, and the author of the finalize-the-beta-list message; and (d) the casual-breaks group whose members are me, the author of the finalize-the-beta-list message, and the person who started that casual-breaks chat.

Return the two newly created group objects and the three messages you posted (the broadcast plus the two threaded replies).
```

### What the judge checks at L4

- **carry:c0a1:text**
    - a correct answer says: The message posted into the group where the finalize-the-beta-list request appears states that the acting user belongs to four chats: (1) the group where the finalize-the-beta-list request appears, whose members are the acting user, the author of the finalize-the-beta-list message, and the author of the capacity-concern message; (2) a one-on-one DM between the acting user and the author of the final-assets question; (3) a group whose members are the acting user, the author of the revised-hero post, and the author of the finalize-the-beta-list message; and (4) the casual-breaks group whose members are the acting user, the author of the finalize-the-beta-list message, and the person who started that casual-breaks chat.
    - where to look: Look in the body of the message posted into the group where the finalize-the-beta-list request was made.
- **carry:c1a1:text**
    - a correct answer says: The threaded reply posted in response to the capacity-concern message states that the acting user belongs to four chats: (1) the group where the finalize-the-beta-list request appears, whose members are the acting user, the author of the finalize-the-beta-list message, and the author of the capacity-concern message; (2) a one-on-one DM between the acting user and the author of the final-assets question; (3) a group whose members are the acting user, the author of the revised-hero post, and the author of the finalize-the-beta-list message; and (4) the casual-breaks group whose members are the acting user, the author of the finalize-the-beta-list message, and the person who started that casual-breaks chat.
    - where to look: Look in the text of the threaded reply posted to the capacity-concern message.
- **carry:c0a2:text**
    - a correct answer says: The threaded reply posted in response to the revised-hero post states that the acting user belongs to four chats: (1) the group where the finalize-the-beta-list request appears, whose members are the acting user, the author of the finalize-the-beta-list message, and the author of the capacity-concern message; (2) a one-on-one DM between the acting user and the author of the final-assets question; (3) a group whose members are the acting user, the author of the revised-hero post, and the author of the finalize-the-beta-list message; and (4) the casual-breaks group whose members are the acting user, the author of the finalize-the-beta-list message, and the person who started that casual-breaks chat.
    - where to look: Look in the text of the threaded reply posted to the revised-hero message.

## Warnings recorded for this task

- v2: pasted the description 'the message about worried about capacity for' 2 times; introduce a thing once, then refer back to it
- v2: pasted the description 'the message about Pushed the revised hero' 2 times; introduce a thing once, then refer back to it
- v3: pasted the description 'the message about worried about capacity for' 2 times; introduce a thing once, then refer back to it
- v3: pasted the description 'the message about Pushed the revised hero' 2 times; introduce a thing once, then refer back to it
- v4: still enumerates 4 step(s)
- v4: 3 sequencing connective(s) — reads as a list in prose clothing
