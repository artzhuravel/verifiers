# The ladder — t8

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
| `$user_0` | Cara Singh @cara | `u_cara` | "whoever wrote the message about start a bisection tomorrow" | 1/1/0 |
| `$message_0` | in c_002 from Ben Ortiz, unread by you: "Quick Q: who is the mai | `m_002` | "the message about maintainer of the 'data-toolkit" | 2/1/0 |
| `$message_1` | in release-planning from Dan Park, unread by you: 'We need to lo | `m_005` | "the message about upstream maintainer for licensing" | 1/1/0 |
| `$chat_0` | group 'spark-lib' — members: You @you, Alice Kim @alice, Ben Ort | `c_001` | "the spark-lib channel" | 1/1/0 |

## L1 — explicit, numbered, ids named. The floor.

```text
1. Run get_user with user_id = u_cara to look up Cara Singh (@cara) and record the returned user object.
2. Run ask_question on repoName = 'pandas-dev/pandas' with question "What is this project's purpose?" and save the free-text answer; you must include that answer in your final reply.
3. Reply to message m_002 (in chat c_002) with a message whose text includes the value returned by step 1 (i.e., include Cara's user/handle exactly as returned by get_user).
4. Reply to message m_005 (in chat c_003) with a message whose text includes the value returned by step 1 (i.e., include Cara's user/handle exactly as returned by get_user).
5. Send a message to chat c_001 (spark-lib) whose text includes the value returned by step 1 (i.e., include Cara's user/handle exactly as returned by get_user).
6. Reply to the message you created in step 3 with the exact text: "Thanks — I'll ping Cara (@cara) to confirm the upstream repo and licensing."
```

### What the judge checks at L1

- **report:c2a0**
    - a correct answer says: Pandas is a Python library that provides high-performance, user-friendly data structures (notably DataFrame and Series) and tools for data manipulation and analysis of structured/tabular data.
    - where to look: Look in the agent's final reply for the sentence reporting the answer returned by the ask_question about pandas-dev/pandas (the project's purpose).
- **carry:c0a1:text**
    - a correct answer says: The reply to Ben (the threaded reply to message m_002) includes Cara's handle @cara.
    - where to look: Check the text of the reply the agent posted in thread replying to message m_002 in chat c_002.
- **carry:c1a0:text**
    - a correct answer says: The reply to Dan (the threaded reply to message m_005) includes Cara's handle @cara.
    - where to look: Check the text of the reply the agent posted in thread replying to message m_005 in chat c_003.
- **carry:c0a2:text**
    - a correct answer says: The message sent to the spark-lib group (chat c_001) includes Cara's handle @cara.
    - where to look: Check the text of the message the agent sent to chat c_001 (spark-lib).

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
Look up, by id, whoever wrote the message about start a bisection tomorrow and record the returned user object; then ask the GitHub repository 'pandas-dev/pandas' the question "What is this project's purpose?" and save the free-text answer so you can report it in your final reply. After that, post a threaded reply to the message about maintainer of the 'data-toolkit' whose text includes the user object you looked up (i.e., include that person's handle exactly as returned). Then post a threaded reply to the message about upstream maintainer for licensing whose text also includes that same user object. Next send a message to the spark-lib channel whose text includes that same user object. Finally, reply to the threaded reply you made to the message about maintainer of the 'data-toolkit' with the exact text: "Thanks — I'll ping Cara (@cara) to confirm the upstream repo and licensing.", and report back when all of the above are done.
```

### What the judge checks at L2

- **report:c2a0**
    - a correct answer says: Pandas is a Python library that provides high-performance, user-friendly data structures (notably DataFrame and Series) and tools for data manipulation and analysis of structured/tabular data.
    - where to look: Look in the agent's final reply for the sentence reporting the answer returned by the question asked about the repository 'pandas-dev/pandas' (the question: "What is this project's purpose?").
- **carry:c0a1:text**
    - a correct answer says: The reply to the message about maintainer of the 'data-toolkit' includes Cara's handle @cara.
    - where to look: Check the text of the reply the agent posted in the thread replying to the message about maintainer of the 'data-toolkit' (the DM that asked who maintains the vendored 'data-toolkit').
- **carry:c1a0:text**
    - a correct answer says: The reply to the message about upstream maintainer for licensing includes Cara's handle @cara.
    - where to look: Check the text of the reply the agent posted in the thread replying to the message about upstream maintainer for licensing (the release-planning thread asking for the maintainer's contact).
- **carry:c0a2:text**
    - a correct answer says: The message sent to the spark-lib channel includes Cara's handle @cara.
    - where to look: Check the text of the message the agent sent to the spark-lib channel.

## L3 — the goal. No step individually identifiable.

```text
Look up, by id, whoever wrote the message about start a bisection tomorrow and keep the returned user object for reuse. Ask the GitHub repository 'pandas-dev/pandas' the question "What is this project's purpose?" and save the free-text answer so you can report it in your final reply. Post a threaded reply to the message about maintainer of the 'data-toolkit' whose text includes that user object exactly as returned (use the returned handle when composing the text). Post a threaded reply to the message about upstream maintainer for licensing that also includes the same returned user object. Send a message to the spark-lib channel that includes the same returned user object. Then reply to the threaded reply you posted in the maintainer thread with a message that is exactly: Thanks — I'll ping <that user's display name> (<that user's handle>) to confirm the upstream repo and licensing. Finally, provide a final report that confirms each action completed and includes the answer you saved from asking 'pandas-dev/pandas' the question "What is this project's purpose?".
```

### What the judge checks at L3

- **report:c2a0**
    - a correct answer says: The final report states that Pandas is a Python library providing high-performance, user-friendly data structures (notably DataFrame and Series) and tools for data manipulation and analysis of structured/tabular data.
    - where to look: Look in the agent's final report for the sentence that reports the answer returned to the question asked about the repository 'pandas-dev/pandas' (the question: "What is this project's purpose?").
- **carry:c0a1:text**
    - a correct answer says: The threaded reply to the message about maintainer of the 'data-toolkit' includes the handle of the user found by looking up whoever wrote the message about start a bisection tomorrow, exactly as that lookup returned it.
    - where to look: Check the text of the reply the agent posted in the thread replying to the message about maintainer of the 'data-toolkit' (the DM that asked who maintains the vendored 'data-toolkit').
- **carry:c1a0:text**
    - a correct answer says: The threaded reply to the message about upstream maintainer for licensing includes the handle of the same user found by looking up whoever wrote the message about start a bisection tomorrow, exactly as that lookup returned it.
    - where to look: Check the text of the reply the agent posted in the thread replying to the message about upstream maintainer for licensing (the release-planning thread asking for the maintainer's contact).
- **carry:c0a2:text**
    - a correct answer says: The message sent to the spark-lib channel includes the handle of the same user found by looking up whoever wrote the message about start a bisection tomorrow, exactly as that lookup returned it.
    - where to look: Check the text of the message the agent sent to the spark-lib channel.

## L4 — folded. Actions that existed only to feed each other become one request, no content is dictated word for word, and no clause narrates a hand-off.

```text
Find the user who authored the message that said they'd start a bisection tomorrow; get that person's display name and handle from their workspace profile. Query the GitHub repository 'pandas-dev/pandas' to find what the project exists to do, and keep that answer to include in your final report. In the direct message that asks who maintains the vendored 'data-toolkit', post a threaded reply that includes that person's handle exactly as it appears in their workspace profile. In the release-planning thread that asks for the upstream maintainer contact, post a threaded reply that includes the same handle exactly as it appears in their profile. Send a message to the spark-lib group that mentions the same handle exactly as it appears in their profile. Then add a follow-up reply in the maintainer DM thread saying you will ping that person to confirm the upstream repo and licensing, and mention their display name and handle. Finally, post a concise final report here that confirms each action was completed and includes the answer you obtained about what 'pandas-dev/pandas' is for.
```

### What the judge checks at L4

- **report:c2a0**
    - a correct answer says: The final report states that Pandas is a Python library providing high-performance, user-friendly data structures (notably DataFrame and Series) and tools for data manipulation and analysis of structured/tabular data.
    - where to look: Look in the agent's final report (the last reply it posts here) for the sentence that reports what 'pandas-dev/pandas' is for.
- **carry:c0a1:text**
    - a correct answer says: The threaded reply posted in the direct message that asks who maintains the vendored 'data-toolkit' includes the handle of the person who wrote the message about starting a bisection tomorrow, exactly as that handle appears in that person's workspace profile.
    - where to look: Check the text of the reply the agent posted in the DM thread asking who maintains the vendored 'data-toolkit'.
- **carry:c1a0:text**
    - a correct answer says: The threaded reply posted in the release-planning thread that asks for the upstream maintainer contact includes the same handle of the person who wrote the message about starting a bisection tomorrow, exactly as that handle appears in that person's workspace profile.
    - where to look: Check the text of the reply the agent posted in the release-planning thread requesting the maintainer's contact.
- **carry:c0a2:text**
    - a correct answer says: The message sent to the spark-lib group includes the same handle of the person who wrote the message about starting a bisection tomorrow, exactly as that handle appears in that person's workspace profile.
    - where to look: Check the text of the message the agent sent to the spark-lib channel.

## Warnings recorded for this task

- stage 5 dropped: message n4: message 'n4' is from 'n1', who is not in 'c2'
- v2: named 'cara'
- v2: pasted the description "the message about maintainer of the 'data-toolkit" 2 times; introduce a thing once, then refer back to it
- v2: judge item carry:c0a1:text: still names 'cara'
- v2: judge item carry:c1a0:text: still names 'cara'
- v2: judge item carry:c0a2:text: still names 'cara'
- v3: 1 sequencing connective(s) — reads as a list in prose clothing
- v4: 2 sequencing connective(s) — reads as a list in prose clothing
