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
| `$user_0` | Person 0 @person0 | `u_person0` | "whoever wrote the message about concerns widget 0 and" | 0/0/0 |
| `$message_0` | in room-0 from Person 0, unread by you: 'note 0 concerns widget  | `m_001` | "the message about concerns widget 0 and" | 0/0/0 |
| `$chat_0` | group 'room-0' — members: You @you, Person 0 @person0, Extra 0 @ | `c_001` | "the conversation where concerns widget 0 and came up" | 0/0/0 |

## L1 — explicit, numbered, ids named. The floor.

```text
CANNED v1 text — this run exists for the prompts, not the prose.
```

### What the judge checks at L1

- **carry:c0a1:text**
    - a correct answer says: canned expected answer
    - where to look: the message step 4 posts
- **carry:c0a2:text**
    - a correct answer says: canned expected answer
    - where to look: the message step 5 posts
- **carry:c1a1:text**
    - a correct answer says: canned expected answer
    - where to look: the message step 6 posts
- **report:c1a2**
    - a correct answer says: canned expected answer
    - where to look: the agent's final reply

## L2 — prose. Every id replaced by the description proved to single it out, so the agent must inspect the workspace before it can act at all.

```text
CANNED prompt_v2 text — this run exists for the prompts.
```

### What the judge checks at L2

- **carry:c0a1:text**
    - a correct answer says: canned expected, restated at prompt_v2
    - where to look: the message step 4 posts
- **carry:c0a2:text**
    - a correct answer says: canned expected, restated at prompt_v2
    - where to look: the message step 5 posts
- **carry:c1a1:text**
    - a correct answer says: canned expected, restated at prompt_v2
    - where to look: the message step 6 posts
- **report:c1a2**
    - a correct answer says: canned expected, restated at prompt_v2
    - where to look: the agent's final reply

## L3 — the goal. No step individually identifiable.

```text
CANNED prompt_v3 text — this run exists for the prompts.
```

### What the judge checks at L3

- **carry:c0a1:text**
    - a correct answer says: canned expected, restated at prompt_v3
    - where to look: the message step 4 posts
- **carry:c0a2:text**
    - a correct answer says: canned expected, restated at prompt_v3
    - where to look: the message step 5 posts
- **carry:c1a1:text**
    - a correct answer says: canned expected, restated at prompt_v3
    - where to look: the message step 6 posts
- **report:c1a2**
    - a correct answer says: canned expected, restated at prompt_v3
    - where to look: the agent's final reply

## L4 — folded. Actions that existed only to feed each other become one request, no content is dictated word for word, and no clause narrates a hand-off.

```text
CANNED prompt_v4 text — this run exists for the prompts.
```

### What the judge checks at L4

- **carry:c0a1:text**
    - a correct answer says: canned expected, restated at prompt_v4
    - where to look: the message step 4 posts
- **carry:c0a2:text**
    - a correct answer says: canned expected, restated at prompt_v4
    - where to look: the message step 5 posts
- **carry:c1a1:text**
    - a correct answer says: canned expected, restated at prompt_v4
    - where to look: the message step 6 posts
- **report:c1a2**
    - a correct answer says: canned expected, restated at prompt_v4
    - where to look: the agent's final reply

## Warnings recorded for this task

- v2: never uses the description 'whoever wrote the message about concerns widget 0 and'; the thing it picks out is either unreferenced or referred to some other way, which nothing has checked resolves
- v2: never uses the description 'the message about concerns widget 0 and'; the thing it picks out is either unreferenced or referred to some other way, which nothing has checked resolves
- v2: never uses the description 'the conversation where concerns widget 0 and came up'; the thing it picks out is either unreferenced or referred to some other way, which nothing has checked resolves
- v2: judge item carry:c0a1:text: still refers to a step by number
- v2: judge item carry:c0a2:text: still refers to a step by number
- v2: judge item carry:c1a1:text: still refers to a step by number
- v3: never uses the description 'whoever wrote the message about concerns widget 0 and'; the thing it picks out is either unreferenced or referred to some other way, which nothing has checked resolves
- v3: never uses the description 'the message about concerns widget 0 and'; the thing it picks out is either unreferenced or referred to some other way, which nothing has checked resolves
- v3: never uses the description 'the conversation where concerns widget 0 and came up'; the thing it picks out is either unreferenced or referred to some other way, which nothing has checked resolves
- v3: judge item carry:c0a1:text: still refers to a step by number
- v3: judge item carry:c0a2:text: still refers to a step by number
- v3: judge item carry:c1a1:text: still refers to a step by number
- v4: judge item carry:c0a1:text: still refers to a step by number
- v4: judge item carry:c0a2:text: still refers to a step by number
- v4: judge item carry:c1a1:text: still refers to a step by number
