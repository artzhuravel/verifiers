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
| `$message_0` | in frontend-team from Priya Nair, unread by you: 'Can someone co | `m_001` | "the message about someone confirm the license" | 2/2/0 |
| `$chat_0` | group 'frontend-team' — members: You @you, Priya Nair @priya_p,  | `c_001` | "the conversation where someone confirm the license came up" | 1/1/0 |
| `$chat_1` | group 'sec-ops' — members: You @you, Mateo Ruiz @mateo_r, Jamal  | `c_002` | "the conversation with exactly 3 people in it" | 2/2/0 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Call ask_question with repoName 'loom/widget-lib' and the question "What is the repo's license, primary language, and who are listed as maintainers (from LICENSE, package.json, or GitHub)?" and capture the free-text answer returned. 2. Reply to message m_001 in chat c_001 with the text: "On it — I'll pull the license file path, primary language, and maintainer list for loom/widget-lib and post what I find shortly." 3. Reply to the message you create in step 2 with the text: "Posting the findings in the channel below so everyone can review; will flag any concerns for licensing or maintainers." 4. Send a message to chat c_001 whose body includes the repository license, the primary language, and the full maintainer list exactly as returned by the ask_question call you made in step 1. 5. Reply to message m_001 in chat c_001 with the text: "FYI — I’ll also paste the same findings into sec-ops so Jamal and Mateo can verify." 6. Add the ':+1:' reaction to the message you created in step 3. 7. Send a message to chat c_002 whose body includes the repository license, the primary language, and the full maintainer list exactly as returned by the ask_question call you made in step 1.
```

### What the judge checks at L1

- **carry:c1a0:text**
    - a correct answer says: The message sent to the frontend-team states that the repository's license is MIT, its primary language is TypeScript, and the maintainers listed are Alex Park (alex_p) and Priya Nair (priya_p).
    - where to look: Look in the message posted to chat c_001 in step 4; it should contain the license, primary language, and maintainer names.
- **carry:c1a2:text**
    - a correct answer says: The message sent to the sec-ops channel states that the repository's license is MIT, its primary language is TypeScript, and the maintainers listed are Alex Park (alex_p) and Priya Nair (priya_p).
    - where to look: Look in the message posted to chat c_002 in step 7; it should contain the same license, language, and maintainer list as step 4.

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Please perform these actions in order. First, ask an AI-grounded question about the GitHub repository loom/widget-lib using the exact question "What is the repo's license, primary language, and who are listed as maintainers (from LICENSE, package.json, or GitHub)?" and capture the free-text answer returned. Then post a threaded reply to the message about someone confirm the license with the text: "On it — I'll pull the license file path, primary language, and maintainer list for loom/widget-lib and post what I find shortly." After that, post a reply to that reply with the text: "Posting the findings in the channel below so everyone can review; will flag any concerns for licensing or maintainers." Next, post a message to the conversation where someone confirm the license came up whose body includes the repository license, the primary language, and the full maintainer list exactly as returned by the question you asked. Then post a threaded reply to the message about someone confirm the license that says: "FYI — I’ll also paste the same findings into the conversation with exactly 3 people in it so Jamal and Mateo can verify." After posting that second threaded reply, add the ':+1:' reaction to the reply you made earlier. Finally, post a message to the conversation with exactly 3 people in it whose body includes the repository license, the primary language, and the full maintainer list exactly as returned by the earlier question.
```

### What the judge checks at L2

- **carry:c1a0:text**
    - a correct answer says: The message sent to the conversation where someone confirm the license came up states that the repository's license is MIT, its primary language is TypeScript, and the maintainers listed are Alex Park (alex_p) and Priya Nair (priya_p).
    - where to look: Look in the message posted to the conversation where someone confirm the license came up that contains the findings; it should include the license, primary language, and the maintainer names listed above.
- **carry:c1a2:text**
    - a correct answer says: The message sent to the conversation with exactly 3 people in it states that the repository's license is MIT, its primary language is TypeScript, and the maintainers listed are Alex Park (alex_p) and Priya Nair (priya_p).
    - where to look: Look in the message posted to the conversation with exactly 3 people in it that contains the findings; it should contain the same license, primary language, and maintainer list as the other findings message.

## L3 — the goal. No step individually identifiable.

```text
Use the AI-grounded query tool to ask about the GitHub repository loom/widget-lib with the exact question "What is the repo's license, primary language, and who are listed as maintainers (from LICENSE, package.json, or GitHub)?" Capture the free-text answer you receive. Reply in-thread to the message about someone confirm the license to say you will pull the license file path, the primary language, and the maintainer list for loom/widget-lib and post the findings shortly. Inside that same thread, post a follow-up reply saying you will post the findings in the channel for everyone to review and that you will flag any licensing or maintainer concerns. Post a message to the conversation where someone confirm the license came up whose body contains the repository license, the primary language, and the full maintainer list exactly as returned by your earlier query. Also post a threaded reply to the message about someone confirm the license noting you will paste the same findings into the conversation with exactly 3 people in it so the people there can verify. Add the ':+1:' reaction to the follow-up reply you posted in the thread. Finally send a message into the conversation with exactly 3 people in it whose body contains the repository license, the primary language, and the full maintainer list exactly as returned by the AI query.
```

### What the judge checks at L3

- **carry:c1a0:text**
    - a correct answer says: The message sent to the conversation where someone confirm the license came up states that the repository's license is MIT, its primary language is TypeScript, and the maintainers listed are Alex Park (alex_p) and Priya Nair (priya_p).
    - where to look: Look in the message posted to the conversation where someone confirm the license came up that contains the findings; it should include the license, primary language, and the maintainer names listed above.
- **carry:c1a2:text**
    - a correct answer says: The message sent to the conversation with exactly 3 people in it states that the repository's license is MIT, its primary language is TypeScript, and the maintainers listed are Alex Park (alex_p) and Priya Nair (priya_p).
    - where to look: Look in the message posted to the conversation with exactly 3 people in it that contains the findings; it should contain the same license, primary language, and maintainer list as the other findings message.

## L4 — folded. Actions that existed only to feed each other become one request, no content is dictated word for word, and no clause narrates a hand-off.

```text
Run an AI-grounded query for the GitHub repo loom/widget-lib to determine its license, primary programming language, and who is listed as maintainers (check LICENSE, package.json, and GitHub). In the thread started by the message asking someone to confirm the license, post a reply that you will pull the license file path, the primary language, and the maintainer list for loom/widget-lib and will post the findings shortly. In the same thread, post a short follow-up reply that you will post the findings in the channel for everyone to review and that you will flag any licensing or maintainer concerns. Publish the query results into the conversation where that original request appeared: the message you post there must state the repository's license, its primary language, and the full maintainer list exactly as returned by the AI query. Also in the original thread, add a reply saying you will paste the same findings into the conversation with exactly three people in it so they can verify. Add a ':+1:' reaction to the follow-up reply you posted in the thread. Finally, send a message into the three-person conversation that contains the repository license, primary language, and the full maintainer list exactly as returned by the AI query.
```

### What the judge checks at L4

- **carry:c1a0:text**
    - a correct answer says: The message posted to the conversation where someone asked to confirm the license states that the repository's license is MIT, its primary language is TypeScript, and the maintainers listed are Alex Park (alex_p) and Priya Nair (priya_p).
    - where to look: Check the message in the conversation where the original license-confirm request appeared that contains the findings; it should include the license, the primary language, and the maintainer names listed above.
- **carry:c1a2:text**
    - a correct answer says: The message sent to the conversation with exactly three people in it states that the repository's license is MIT, its primary language is TypeScript, and the maintainers listed are Alex Park (alex_p) and Priya Nair (priya_p).
    - where to look: Check the message posted to the three-person conversation that contains the findings; it should include the same license, primary language, and maintainer list as the other findings message.

## Warnings recorded for this task

- stage 5 dropped: chat n2: would make 'the chat that has exactly 3 members, and is the only chat with that many' stop singling out $chat_1
- stage 5 dropped: message n9: message 'n9' is in undeclared chat 'n2'
- v2: pasted the description 'the message about someone confirm the license' 2 times; introduce a thing once, then refer back to it
- v2: pasted the description 'the conversation with exactly 3 people in it' 2 times; introduce a thing once, then refer back to it
- v3: pasted the description 'the message about someone confirm the license' 2 times; introduce a thing once, then refer back to it
- v3: pasted the description 'the conversation with exactly 3 people in it' 2 times; introduce a thing once, then refer back to it
