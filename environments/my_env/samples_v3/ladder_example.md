# What the task pipeline does — a worked example

Every task starts as a **deterministically sampled action plan** over a mock chat app
plus a real read-only web tool. An LLM turns that plan into a natural-language prompt,
and then rewrites it four more times, each pass adding one class of difficulty.

The five rungs live in separate files and **contain the same tasks**: for a given task,
the seed world, the expected end state, the action plan and the graded answers are
byte-identical across all five. Only the prompt text differs. So a score difference
between two rungs is caused by the wording, not by having generated different tasks.

| rung | adds |
|---|---|
| **L1** | explicit — the easy floor |
| **L2** | descriptive; step numbers, tool names, ids and handles all forbidden |
| **L3** | relational / temporal references |
| **L4** | conditional logic the agent must resolve against live state |
| **L5** | realistic typos |

Two examples follow. The **action plan** is ground truth — what the agent is scored
against; it never changes between rungs. `[INVALID]` steps target deliberately
nonexistent entities and are expected to fail; they are distractors.

---

## Example A — eight actions, rich referential drift

### Action plan (ground truth, identical at every rung)

```
1. [WRITE  ] chat_send_message        {"chat_id": "c_005", "text": "sounds good"}
2. [OPEN   ] deepwiki_ask_question    {}
3. [READ   ] chat_get_user            {"user_id": "u_priya_raman"}
4. [OPEN   ] deepwiki_ask_question    {}
5. [WRITE  ] chat_create_chat         {"member_ids": ["u_maya"], "name": "retro"}
6. [WRITE  ] chat_reply_to            {"message_id": "m_004", "text": "shipping it"}
7. [INVALID] chat_add_reaction        {"message_id": "m_missing", "emoji": ":+1:"}
8. [WRITE  ] chat_add_reaction        {"message_id": "m_016", "emoji": ":eyes:"}
```

### How one entity is named at each rung — the chat the first message goes to (`c_005`)

| rung | how it is referred to |
|---|---|
| L1 | the DM with Alex Chen (Alex @alex.chen) |
| L2 | the one-to-one DM you share with the colleague who asked "Do you have a read on the Q3 date?" |
| L3 | the one-to-one DM thread where the other person most recently asked "Do you have a read on the Q3 date?" |
| L4 | (unchanged from L3) |
| L5 | (unchanged from L3) |

### L1 — explicit  (2049 chars)

> Numbered steps, and the operations are named outright. Entities are handed over directly — `@alex.chen`, `Priya @praman (handle u_priya_raman)`, `message m_016`. Nothing has to be looked up.

```text
Please carry out these operations in order and report back as specified.

1) Send the message "sounds good" in the DM with Alex Chen (Alex @alex.chen). This is the one-to-one DM you share with Alex (the DM that currently contains his question about the Q3 date).

2) Look up the GitHub repo facebook/react and answer this question exactly: "What license is facebook/react released under and what's its primary programming language?" Keep the answer short (a sentence or two); you will insert this answer later into the reply described in step 6.

3) Retrieve the user record for Priya on the design side: Priya @praman (handle u_priya_raman). Just look up her user info.

4) Look up the GitHub repo tensorflow/tensorflow and answer this question exactly: "What is the main purpose of tensorflow/tensorflow and which language is it primarily written in?" Keep the answer short (a sentence or two); you will insert this answer later into the reply described in step 6.

5) Create a new chat named "retro" that includes only Maya (@maya) as the other member.

6) Reply to the message from Priya @priya.nair in the 'launch' channel that reads: "If it slips we have to redo the press embargo." (that is the Priya message in the launch channel). Replace the placeholder text with the two DeepWiki answers you produced in steps 2 and 4. Put both answers into this single reply message, clearly labeled so it's obvious which answer corresponds to facebook/react and which corresponds to tensorflow/tensorflow.

7) Attempt to add a +1 reaction to the message ID m_missing (this ID does not exist in the workspace; perform the reaction-add operation targeting message_id = "m_missing" with emoji ":+1:").

8) Add an :eyes: reaction to the message in the 'design-review' channel that reads "Step 3 asks for too much before showing any value." (Hana @hana's message, message m_016). Use that message ID (m_016) and add the :eyes: emoji.

Perform the steps in the order listed. Put the text answers from steps 2 and 4 together into the reply to Priya in step 6.
```

### L2 — descriptive / de-scaffolded  (1688 chars)

> Scaffolding stripped: continuous prose, no numbering, no operation names, no ids, no handles. Every entity becomes a description of itself.

```text
Please carry out these actions and report back exactly as described. Send the message "sounds good" in the one-to-one DM you share with the colleague who asked "Do you have a read on the Q3 date?". Look up the repository facebook/react and answer this question exactly: "What license is facebook/react released under and what's its primary programming language?" Keep the answer short (a sentence or two); you will put this answer into a reply to the launch-channel message that reads "If it slips we have to redo the press embargo." Retrieve the user record for the designer who put the new onboarding flow up for review. Look up the repository tensorflow/tensorflow and answer this question exactly: "What is the main purpose of tensorflow/tensorflow and which language is it primarily written in?" Keep the answer short (a sentence or two); you will put this answer into the same reply to the launch-channel message that reads "If it slips we have to redo the press embargo." Create a new chat named "retro" that includes only the other member who wrote "I can move the embargo to the 14th, but not past it." Reply to the message in the launch channel that reads "If it slips we have to redo the press embargo." Replace any placeholder text with the two answers you produced above, putting both answers into this single reply and clearly labeling which answer corresponds to facebook/react and which corresponds to tensorflow/tensorflow. Attempt to add a +1 reaction to the message with id m_missing using the :+1: emoji. Add an :eyes: reaction to the message in the channel where the new onboarding flow is up for review that reads "Step 3 asks for too much before showing any value."
```

### L3 — relational / temporal  (1705 chars)

> References turn relational and temporal — *most recently posted*, *oldest unread*. These cannot be resolved by reading the prompt; the agent has to go and look.

```text
Please carry out these actions and report back exactly as described. In the one-to-one DM thread where the other person most recently asked "Do you have a read on the Q3 date?", send the message "sounds good". Look up the repository facebook/react and answer this question exactly: "What license is facebook/react released under and what's its primary programming language?" Keep the answer short (a sentence or two); put this answer into a reply to the oldest unread message in the launch channel that reads "If it slips we have to redo the press embargo." Retrieve the user record for the person who most recently posted in the design-review discussion announcing the new onboarding flow. Look up the repository tensorflow/tensorflow and answer this question exactly: "What is the main purpose of tensorflow/tensorflow and which language is it primarily written in?" Keep the answer short (a sentence or two); put this answer into the same reply to the launch-channel message that reads "If it slips we have to redo the press embargo." Create a new chat named "retro" that includes only the other member in the launch channel who wrote "I can move the embargo to the 14th, but not past it." Reply to the launch channel message that reads "If it slips we have to redo the press embargo." Replace any placeholder text in that reply with both answers you produced above, clearly labeling which answer corresponds to facebook/react and which corresponds to tensorflow/tensorflow. Attempt to add a +1 reaction to the message with id m_missing using the :+1: emoji. Add an :eyes: reaction to the message in the design-review chat where the participant said "Step 3 asks for too much before showing any value."
```

### L4 — conditional  (1886 chars)

> One request moves behind a condition that must be evaluated against live state, with a plausible alternative branch. The condition is true in this workspace, so the planned action is the one that fires.

```text
Please carry out the following actions and report back exactly as described. In the one-to-one DM thread where the other person most recently asked "Do you have a read on the Q3 date?", send the message "sounds good". Look up the repository facebook/react and answer this question exactly: "What license is facebook/react released under and what's its primary programming language?" Keep the answer short (a sentence or two); put this answer into a reply to the oldest unread message in the launch channel that reads "If it slips we have to redo the press embargo." Retrieve the user record for the person who most recently posted in the design-review discussion announcing the new onboarding flow. Look up the repository tensorflow/tensorflow and answer this question exactly: "What is the main purpose of tensorflow/tensorflow and which language is it primarily written in?" Keep the answer short (a sentence or two); put this answer into the same reply to the launch-channel message that reads "If it slips we have to redo the press embargo." If the message in the launch channel that reads "I can move the embargo to the 14th, but not past it." has any reactions, create a new chat named "retro" that includes only the other member in the launch channel who wrote that message; otherwise, create a new chat named "retro" that includes all members of the launch channel. Reply to the launch channel message that reads "If it slips we have to redo the press embargo." Replace any placeholder text in that reply with both answers you produced above, clearly labeling which answer corresponds to facebook/react and which corresponds to tensorflow/tensorflow. Attempt to add a +1 reaction to the message with id m_missing using the :+1: emoji. Add an :eyes: reaction to the message in the design-review chat where the participant said "Step 3 asks for too much before showing any value."
```

### L5 — noisy  (1888 chars)

> Two to five typos, in the prose only. Quoted strings, repository names and identifiers are copied through untouched — the graded answers are keyed to them.

```text
Pleasse carry out the following actions and report back exactly as described. In the one-to-one DM thread where the other person most recently asked "Do you have a read on the Q3 date?", send the message "sounds good". Lookk up the repository facebook/react and answer this question exactly: "What license is facebook/react released under and what's its primary programming language?" Keep the answer short (a sentence or two); put this answer into a reply to the oldest unread message in the launch channel that reads "If it slips we have to redo the press embargo." retrieve the user record for the person who most recently posted in the design-review discussion announcing the new onboarding flow. Look up the repository tensorflow/tensorflow and answer this question exactly: "What is the main purpose of tensorflow/tensorflow and which language is it primarily written in?" Keep the answer short (a sentence or two); put this answer into the same reply to the launch-channel message that reads "If it slips we have to redo the press embargo." If the message in the launch channel that reads "I can move the embargo to the 14th, but not past it." has any reactions, create a new chat named "retro" that includes only the other member in the launch channel who wrote that message; otherwise, create a new chat named "retro" that includes all members of the launch channel. Reply to the launch channel message that reads "If it slips we have to redo the press embargo." Replace any placeholder text in that reply with both answers you produced above, clearly labeling which answer corresponds to facebook/react and which corresponds to tensorflow/tensorflow. Attempt to add a +1 reaction to the message with id m_missing using the :+1: emoji. Add an :eyes: reaction to the message in the design-review chat where the participant said "Step 3 asks for too much before showing any value."
```

---

## Example B — seven actions, three distractors, heavy compression

### Action plan (ground truth, identical at every rung)

```
1. [INVALID] chat_add_reaction        {"message_id": "m_missing", "emoji": ":+1:"}
2. [READ   ] chat_list_chats          {}
3. [INVALID] chat_send_message        {"chat_id": "c_missing", "text": "shipping it"}
4. [INVALID] chat_get_user            {"user_id": "u_missing"}
5. [WRITE  ] chat_mark_read           {"chat_id": "c_006"}
6. [OPEN   ] deepwiki_read_wiki_contents {}
7. [WRITE  ] chat_create_chat         {"member_ids": ["u_hana", "u_priya_nair"], "name": "retro"}
```

### How one entity is named at each rung — the chat to mark read (`c_006`)

| rung | how it is referred to |
|---|---|
| L1 | the group chat named "watercooler" ... (Maya, Diego, Rosa, Yusuf, Ingrid, Hana); internal id c_006 |
| L2 | the group chat that contains the message saying "The espresso machine is making a new noise" and the subsequent messages where the machine was nicknamed Gerald |
| L3 | the oldest unread chat where Maya first posted "The espresso machine is making a new noise" ... |
| L4 | If Maya's message ... is still unread by you, mark as read ...; otherwise do not mark anything |
| L5 | (as L4, with typos elsewhere in the prose) |

### L1 — explicit  (1777 chars)

> Same explicit style. Note steps 1, 3 and 4 target deliberately nonexistent ids: these are distractors the agent is expected to attempt and see fail.

```text
Please run these operations in order and report back the DeepWiki finding in your reply to me when you're done.

1) Attempt to add a +1 reaction to the message with id "m_missing" (i.e., call the add-reaction operation targeting message_id = "m_missing" with emoji ":+1:"). Note: this message id does not exist, but still attempt the operation.

2) List all chats (i.e., call the list-chats operation to retrieve the current chat list).

3) Attempt to send the text "shipping it" into the chat with id "c_missing" (i.e., call the send-message operation targeting chat_id = "c_missing" and text = "shipping it"). Note: that chat id does not exist, but still attempt the operation.

4) Attempt to look up the user with id "u_missing" (i.e., call the get-user operation for user_id = "u_missing"). Note: that user id does not exist, but still attempt the lookup.

5) Mark the watercooler group chat as read (i.e., call the mark-read operation for the group chat named "watercooler" that contains Maya (@maya), Diego (@diego), Rosa (@rosa), Yusuf (@yusuf), Ingrid (@ingrid), and Hana (@hana); internal id c_006).

6) Using the DeepWiki repo reader, look up the GitHub repository "facebook/react" and answer this specific question: "For the GitHub repository 'facebook/react', what is the primary programming language, what license does it use, and provide a one-sentence description of the project's purpose?" After you fetch that from the wiki, let me know what you find in your reply (do not post it into any chat).

7) Create a new group chat named "retro" that contains Hana (@hana) and Priya Nair (@priya.nair) (i.e., call create-chat with members u_hana and u_priya_nair and name "retro").

When you finish, include the DeepWiki answer to step 6 directly in your reply to me.
```

### L2 — descriptive / de-scaffolded  (1047 chars)

> 1777 -> 1047 characters. The `watercooler` chat and the two named colleagues are replaced by what was said in them.

```text
Please perform the following operations in order and then tell me the wiki result in your reply. Add a +1 reaction to the message with id "m_missing". List all chats. Send the text "shipping it" into the chat with id "c_missing". Look up the user with id "u_missing". Mark as read the group chat that contains the message saying "The espresso machine is making a new noise" and the subsequent messages where the machine was nicknamed Gerald. Using the wiki reader, look up this exact question for the GitHub repository 'facebook/react': For the GitHub repository 'facebook/react', what is the primary programming language, what license does it use, and provide a one-sentence description of the project's purpose? When you fetch that from the wiki, let me know what you find in your reply to me (do not post it into any chat). Finally, create a new group chat named "retro" that includes the colleague who posted the message saying "Step 3 asks for too much before showing any value" and the designer who put the new onboarding flow up for review.
```

### L3 — relational / temporal  (1031 chars)

> Tightens the same references and adds ordering (*oldest unread*).

```text
Please carry out these actions in order and then tell me the wiki result in your reply. Add a +1 reaction to the message with id "m_missing". List all chats. Send the text "shipping it" into the chat with id "c_missing". Look up the user with id "u_missing". Mark as read the oldest unread chat where Maya first posted "The espresso machine is making a new noise" and the subsequent messages in that same thread that began calling the machine Gerald. Look up this exact question in the wiki for the GitHub repository 'facebook/react': For the GitHub repository 'facebook/react', what is the primary programming language, what license does it use, and provide a one-sentence description of the project's purpose? When you fetch that from the wiki, let me know what you find in your reply to me (do not post it into any chat). Finally, create a new group chat named "retro" that includes the person who posted "Step 3 asks for too much before showing any value" and the person who first said the new onboarding flow is up for review.
```

### L4 — conditional  (1120 chars)

> The mark-as-read request becomes conditional on whether the message is still unread — which is true here, so the planned action fires.

```text
Please carry out these actions in order and then tell me the wiki result in your reply. Add a +1 reaction to the message with id "m_missing". List all chats. Send the text "shipping it" into the chat with id "c_missing". Look up the user with id "u_missing". If Maya's message "The espresso machine is making a new noise" is still unread by you, mark as read the oldest unread chat where that message and the subsequent messages in that same thread that began calling the machine Gerald appear; otherwise do not mark anything in that chat. Look up this exact question in the wiki for the GitHub repository 'facebook/react': For the GitHub repository 'facebook/react', what is the primary programming language, what license does it use, and provide a one-sentence description of the project's purpose? When you fetch that from the wiki, let me know what you find in your reply to me (do not post it into any chat). Finally, create a new group chat named "retro" that includes the person who posted "Step 3 asks for too much before showing any value" and the person who first said the new onboarding flow is up for review.
```

### L5 — noisy  (1118 chars)

> Typos in prose only; the three sentinel ids survive exactly, since the agent is meant to attempt them verbatim.

```text
Please carry out these actions in order and then tell me the wiki result in your reply. Add a +1 reaciton to the message with id "m_missing". List all chats. Send the text "shipping it" into teh chat with id "c_missing". look up the user with id "u_missing". If Maya's message "The espresso machine is making a new noise" is still unread by you, mark as read the oldest unread chat where that message and the subsequent messages in that same thread that began calling the machine Gerald appear; otherwise do not mark anything in that chat. Look up this exact question in the wiki for the GitHub repository 'facebook/react': For the GitHub repository 'facebook/react', what is the primary programming language, what license does it use, and provide a one-sentence description of the project's purpose? When you fetch that from the wiki, let me know what you find in your reply to me (dont post it into any chat). Finlaly, create a new group chat named "retro" that includes the person who posted "Step 3 asks for too much before showing any value" and the person who first said the new onboarding flow is up for review.
```

---

## What is guaranteed to survive every rewrite

The rewriter is given the original plan and app state each time, not just the previous
prompt, and is held to a fixed set of invariants:

1. A correct reading produces **exactly the planned actions, in order** — nothing added,
   dropped or turned from a read into a write. (A conditional may describe an alternative
   the agent correctly decides against.)
2. Repository names and question text are reproduced **character for character** — the
   expected answers are keyed to them.
3. Each answer is delivered where the plan says: into a specific existing message, or in
   the agent's reply. Never into a message the plan does not contain.
4. Every reference still resolves to **exactly one** entity.
5. It must read as an ordinary work request — no mention of rules, steps, tools or
   scoring, and no explaining why a destination was chosen.
6. Once scaffolding is gone it stays gone: no numbering, tool names or raw ids at any
   rung above L1. The only exception is the deliberately nonexistent sentinel ids.
7. A description must make the reader do the work: no parenthetical that answers the
   reference it just posed, and no index of quoted messages to point back into.

## Known gap

Nothing verifies that a rewrite kept the intent uniquely recoverable. A damaged prompt
and a genuinely hard one score the same, so prompts at L3 and above are worth reading
before being trusted.
