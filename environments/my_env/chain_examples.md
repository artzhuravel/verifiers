# Chain examples

Ten batches from `gen_dependency_chains`, spanning the config space. The machine-readable
form is `chain_examples.json`; this file is the same data rendered for reading.

`→param=id` is an **object** edge — the id is bound, so placement is deterministically
checkable. `→param (content)` is a **value** edge — the argument shown is sampled filler,
and turning it into a real obligation is the authoring step's job.

## 1. two short self-contained errands

The floor: two independent strands, nothing crossing, nothing skipped. A prompt for this is two unrelated requests in one message.

```text
chain 0: max_depth=2  max_breadth=1  p_skip=0.0  p_cross=0.0  p_unrelated=0.0
chain 1: max_depth=2  max_breadth=1  p_skip=0.0  p_cross=0.0  p_unrelated=0.0
seed=3  max_global_depth=None  ->  2 turns, 4 actions (4 links + 0 distractors), depths [2, 2]
edges: 2 total, 0 crossing threads, 2 object / 0 value, widest fan-in 1
```

```text
turn 0
  chain0 c0a0  create_chat          member_ids=["u_lena", "u_noor"], name="<name>"
                                    <- root
  chain1 c1a0  send_message         chat_id="c_002", text="<text>"
                                    <- root
turn 1
  chain0 c0a1  send_message         chat_id="c_007", text="<text>"
                                    <- c0a0→chat_id=c_007
  chain1 c1a1  add_reaction         message_id="m_041", emoji="<emoji>"
                                    <- c1a0→message_id=m_041
```

## 2. one linear errand, four deep

A single strand where each step feeds the next — the simplest thing that still needs to be described in order.

```text
chain 0: max_depth=4  max_breadth=1  p_skip=0.0  p_cross=0.0  p_unrelated=0.0
seed=5  max_global_depth=None  ->  4 turns, 4 actions (4 links + 0 distractors), depths [4]
edges: 3 total, 0 crossing threads, 0 object / 3 value, widest fan-in 1
```

```text
turn 0
  chain0 c0a0  read_wiki_structure  (open-ended: repo/question chosen at authoring time)
                                    <- root
turn 1
  chain0 c0a1  send_message         chat_id="c_003", text="<text>"
                                    <- c0a0→text (content)
turn 2
  chain0 c0a2  reply_to             message_id="m_027", text="<text>"
                                    <- c0a0→text (content)
turn 3
  chain0 c0a3  reply_to             message_id="m_040", text="<text>"
                                    <- c0a0→text (content)
```

## 3. fan-in synthesis

High breadth with full crossing, so one action gathers several earlier results. This is the 'one message carrying what two lookups found' case.

```text
chain 0: max_depth=2  max_breadth=3  p_skip=0.0  p_cross=1.0  p_unrelated=0.0
chain 1: max_depth=2  max_breadth=3  p_skip=0.0  p_cross=1.0  p_unrelated=0.0
chain 2: max_depth=2  max_breadth=3  p_skip=0.0  p_cross=1.0  p_unrelated=0.0
seed=11  max_global_depth=None  ->  2 turns, 6 actions (6 links + 0 distractors), depths [2, 2, 2]
edges: 7 total, 5 crossing threads, 0 object / 7 value, widest fan-in 3
```

```text
turn 0
  chain0 c0a0  read_wiki_contents   (open-ended: repo/question chosen at authoring time)
                                    <- root
  chain1 c1a0  read_wiki_structure  (open-ended: repo/question chosen at authoring time)
                                    <- root
  chain2 c2a0  read_wiki_contents   (open-ended: repo/question chosen at authoring time)
                                    <- root
turn 1
  chain0 c0a1  send_message         chat_id="c_005", text="<text>"
                                    <- c1a0→text (content) + c2a0→text (content) + c0a0→text (content)
  chain1 c1a1  send_message         chat_id="c_001", text="<text>"
                                    <- c2a0→text (content)
  chain2 c2a1  send_message         chat_id="c_001", text="<text>"
                                    <- c2a0→text (content) + c0a0→text (content) + c1a0→text (content)
```

## 4. interleaved, with waiting

Threads skip turns and borrow, so a strand can begin late by picking up another's output. The prompt has to convey ordering without numbering steps.

```text
chain 0: max_depth=2  max_breadth=2  p_skip=0.35  p_cross=0.5  p_unrelated=0.0
chain 1: max_depth=2  max_breadth=2  p_skip=0.35  p_cross=0.5  p_unrelated=0.0
chain 2: max_depth=2  max_breadth=1  p_skip=0.5  p_cross=0.8  p_unrelated=0.0
seed=7  max_global_depth=None  ->  4 turns, 6 actions (6 links + 0 distractors), depths [2, 2, 2]
edges: 4 total, 2 crossing threads, 2 object / 2 value, widest fan-in 1
```

```text
turn 0
  chain2 c2a0  read_wiki_structure  (open-ended: repo/question chosen at authoring time)
                                    <- root
  (silent: chain 0, 1)
turn 1
  chain0 c0a0  send_message         chat_id="c_001", text="<text>"
                                    <- root
  chain1 c1a0  reply_to             message_id="m_015", text="<text>"
                                    <- c2a0→text (content)
  chain2 c2a1  reply_to             message_id="m_003", text="<text>"
                                    <- c2a0→text (content)
turn 2
  chain1 c1a1  add_reaction         message_id="m_042", emoji="<emoji>"
                                    <- c1a0→message_id=m_042
  (silent: chain 0, 2)
turn 3
  chain0 c0a1  reply_to             message_id="m_043", text="<text>"
                                    <- c2a1→message_id=m_043
  (silent: chain 1, 2)
```

## 5. distractor-heavy

Half the actions depend on nothing. The prompt must ask for them without hinting that they are incidental.

```text
chain 0: max_depth=3  max_breadth=1  p_skip=0.0  p_cross=0.2  p_unrelated=0.5
chain 1: max_depth=3  max_breadth=1  p_skip=0.0  p_cross=0.2  p_unrelated=0.5
seed=1  max_global_depth=None  ->  3 turns, 11 actions (6 links + 5 distractors), depths [3, 3]
edges: 4 total, 0 crossing threads, 2 object / 2 value, widest fan-in 1
```

```text
turn 0
  chain0 c0a0  read_messages        chat_id="c_003"
                                    <- root
  chain0 c0a1  create_chat          member_ids=["u_lena", "u_tomas"], name=null
                                    <- distractor
  chain1 c1a0  ask_question         (open-ended: repo/question chosen at authoring time)
                                    <- root
  chain1 c1a1  list_chats           (open-ended: repo/question chosen at authoring time)
                                    <- distractor
turn 1
  chain0 c0a2  reply_to             message_id="m_002", text="<text>"
                                    <- c0a0→text (content)
  chain0 c0a3  read_wiki_structure  (open-ended: repo/question chosen at authoring time)
                                    <- distractor
  chain1 c1a2  reply_to             message_id="m_002", text="<text>"
                                    <- c1a1→text (content)
turn 2
  chain0 c0a4  mark_read            chat_id="c_007"
                                    <- c0a1→chat_id=c_007
  chain0 c0a5  read_wiki_structure  (open-ended: repo/question chosen at authoring time)
                                    <- distractor
  chain1 c1a3  reply_to             message_id="m_042", text="<text>"
                                    <- c1a2→message_id=m_042
  chain1 c1a4  ask_question         (open-ended: repo/question chosen at authoring time)
                                    <- distractor
```

## 6. three independent parallel errands

p_cross=0 throughout, so the three strands never touch — the prompt is three separable sub-tasks that can be done in any order.

```text
chain 0: max_depth=3  max_breadth=1  p_skip=0.0  p_cross=0.0  p_unrelated=0.0
chain 1: max_depth=3  max_breadth=1  p_skip=0.0  p_cross=0.0  p_unrelated=0.0
chain 2: max_depth=3  max_breadth=1  p_skip=0.0  p_cross=0.0  p_unrelated=0.0
seed=17  max_global_depth=None  ->  3 turns, 9 actions (9 links + 0 distractors), depths [3, 3, 3]
edges: 6 total, 0 crossing threads, 5 object / 1 value, widest fan-in 1
```

```text
turn 0
  chain0 c0a0  create_chat          member_ids=["u_jordan_lee", "u_rosa"], name=null
                                    <- root
  chain1 c1a0  ask_question         (open-ended: repo/question chosen at authoring time)
                                    <- root
  chain2 c2a0  create_chat          member_ids=["u_sam_patel", "u_hana"], name="<name>"
                                    <- root
turn 1
  chain0 c0a1  mark_read            chat_id="c_007"
                                    <- c0a0→chat_id=c_007
  chain1 c1a1  send_message         chat_id="c_002", text="<text>"
                                    <- c1a0→text (content)
  chain2 c2a1  mark_read            chat_id="c_008"
                                    <- c2a0→chat_id=c_008
turn 2
  chain0 c0a2  send_message         chat_id="c_007", text="<text>"
                                    <- c0a0→chat_id=c_007
  chain1 c1a2  reply_to             message_id="m_041", text="<text>"
                                    <- c1a1→message_id=m_041
  chain2 c2a2  send_message         chat_id="c_008", text="<text>"
                                    <- c2a0→chat_id=c_008
```

## 7. heavily tangled

Full crossing at breadth 2: the strands are one DAG in practice, and thread identity is only bookkeeping.

```text
chain 0: max_depth=4  max_breadth=2  p_skip=0.0  p_cross=1.0  p_unrelated=0.0
chain 1: max_depth=4  max_breadth=2  p_skip=0.0  p_cross=1.0  p_unrelated=0.0
seed=19  max_global_depth=None  ->  4 turns, 8 actions (8 links + 0 distractors), depths [4, 4]
edges: 8 total, 3 crossing threads, 2 object / 6 value, widest fan-in 2
```

```text
turn 0
  chain0 c0a0  read_wiki_structure  (open-ended: repo/question chosen at authoring time)
                                    <- root
  chain1 c1a0  read_wiki_structure  (open-ended: repo/question chosen at authoring time)
                                    <- root
turn 1
  chain0 c0a1  reply_to             message_id="m_007", text="<text>"
                                    <- c1a0→text (content) + c0a0→text (content)
  chain1 c1a1  send_message         chat_id="c_001", text="<text>"
                                    <- c1a0→text (content)
turn 2
  chain0 c0a2  send_message         chat_id="c_005", text="<text>"
                                    <- c0a0→text (content) + c1a0→text (content)
  chain1 c1a2  reply_to             message_id="m_042", text="<text>"
                                    <- c1a1→message_id=m_042
turn 3
  chain0 c0a3  send_message         chat_id="c_002", text="<text>"
                                    <- c1a0→text (content)
  chain1 c1a3  add_reaction         message_id="m_042", emoji="<emoji>"
                                    <- c1a1→message_id=m_042
```

## 8. asymmetric threads

One fast shallow strand, one slow strand, one deep one. Tests that a prompt can carry sub-tasks of visibly different size.

```text
chain 0: max_depth=1  max_breadth=1  p_skip=0.0  p_cross=0.0  p_unrelated=0.0
chain 1: max_depth=2  max_breadth=2  p_skip=0.6  p_cross=0.5  p_unrelated=0.0
chain 2: max_depth=5  max_breadth=1  p_skip=0.0  p_cross=0.3  p_unrelated=0.0
seed=23  max_global_depth=None  ->  9 turns, 8 actions (8 links + 0 distractors), depths [1, 2, 5]
edges: 5 total, 0 crossing threads, 4 object / 1 value, widest fan-in 1
```

```text
turn 0
  chain0 c0a0  read_messages        chat_id="c_001"
                                    <- root
  chain2 c2a0  send_message         chat_id="c_003", text="<text>"
                                    <- root
  (silent: chain 1)
turn 1
  chain2 c2a1  reply_to             message_id="m_041", text="<text>"
                                    <- c2a0→message_id=m_041
  (silent: chain 0, 1)
turn 2
  chain2 c2a2  reply_to             message_id="m_041", text="<text>"
                                    <- c2a0→message_id=m_041
  (silent: chain 0, 1)
turn 3
  chain2 c2a3  add_reaction         message_id="m_043", emoji="<emoji>"
                                    <- c2a2→message_id=m_043
  (silent: chain 0, 1)
turn 4
  chain2 c2a4  add_reaction         message_id="m_043", emoji="<emoji>"
                                    <- c2a2→message_id=m_043
  (silent: chain 0, 1)
turn 5
  (silent: chain 0, 1, 2)
turn 6
  chain1 c1a0  read_wiki_contents   (open-ended: repo/question chosen at authoring time)
                                    <- root
  (silent: chain 0, 2)
turn 7
  (silent: chain 0, 1, 2)
turn 8
  chain1 c1a1  send_message         chat_id="c_001", text="<text>"
                                    <- c1a0→text (content)
  (silent: chain 0, 2)
```

## 9. everything at once

Wide fan-in, frequent waiting, frequent distractors, heavy crossing — the hardest shape the generator currently produces.

```text
chain 0: max_depth=3  max_breadth=3  p_skip=0.4  p_cross=0.7  p_unrelated=0.4
chain 1: max_depth=3  max_breadth=3  p_skip=0.4  p_cross=0.7  p_unrelated=0.4
chain 2: max_depth=3  max_breadth=3  p_skip=0.4  p_cross=0.7  p_unrelated=0.4
seed=29  max_global_depth=None  ->  6 turns, 11 actions (9 links + 2 distractors), depths [3, 3, 3]
edges: 7 total, 4 crossing threads, 2 object / 5 value, widest fan-in 1
```

```text
turn 0
  chain0 c0a0  reply_to             message_id="m_006", text="<text>"
                                    <- root
  chain2 c2a0  read_messages        chat_id="c_004"
                                    <- root
  (silent: chain 1)
turn 1
  chain0 c0a1  reply_to             message_id="m_013", text="<text>"
                                    <- c2a0→text (content)
  chain2 c2a1  reply_to             message_id="m_020", text="<text>"
                                    <- c2a0→text (content)
  chain2 c2a2  send_message         chat_id="c_004", text="<text>"
                                    <- distractor
  (silent: chain 1)
turn 2
  chain0 c0a2  add_reaction         message_id="m_043", emoji="<emoji>"
                                    <- c2a1→message_id=m_043
  chain1 c1a0  reply_to             message_id="m_024", text="<text>"
                                    <- c2a0→text (content)
  (silent: chain 2)
turn 3
  chain1 c1a1  add_reaction         message_id="m_045", emoji="<emoji>"
                                    <- c1a0→message_id=m_045
  chain2 c2a3  reply_to             message_id="m_043", text="<text>"
                                    <- c2a0→text (content)
  chain2 c2a4  list_chats           (open-ended: repo/question chosen at authoring time)
                                    <- distractor
  (silent: chain 0)
turn 4
  (silent: chain 0, 1, 2)
turn 5
  chain1 c1a2  reply_to             message_id="m_001", text="<text>"
                                    <- c2a4→text (content)
  (silent: chain 0, 2)
```

## 10. globally capped

Deep configs deliberately cut short by max_global_depth, so every strand stops as soon as one reaches depth 2. Useful for short prompts from ambitious configs.

```text
chain 0: max_depth=5  max_breadth=2  p_skip=0.0  p_cross=0.5  p_unrelated=0.0
chain 1: max_depth=5  max_breadth=2  p_skip=0.0  p_cross=0.5  p_unrelated=0.0
chain 2: max_depth=5  max_breadth=2  p_skip=0.0  p_cross=0.5  p_unrelated=0.0
seed=31  max_global_depth=2  ->  2 turns, 6 actions (6 links + 0 distractors), depths [2, 2, 2]
edges: 3 total, 0 crossing threads, 0 object / 3 value, widest fan-in 1
```

```text
turn 0
  chain0 c0a0  ask_question         (open-ended: repo/question chosen at authoring time)
                                    <- root
  chain1 c1a0  read_wiki_structure  (open-ended: repo/question chosen at authoring time)
                                    <- root
  chain2 c2a0  list_chats           (open-ended: repo/question chosen at authoring time)
                                    <- root
turn 1
  chain0 c0a1  reply_to             message_id="m_038", text="<text>"
                                    <- c0a0→text (content)
  chain1 c1a1  reply_to             message_id="m_014", text="<text>"
                                    <- c1a0→text (content)
  chain2 c2a1  send_message         chat_id="c_005", text="<text>"
                                    <- c2a0→text (content)
```
