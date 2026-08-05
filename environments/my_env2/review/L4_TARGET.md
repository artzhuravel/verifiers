# L4 — the target, and why L3 was not it

L3's own output is the argument for a fourth rung. Here is `t1` at L3, verbatim:

> Bring **the one conversation you still have not caught up on** up to date by collecting and
> sharing its recent messages and the result of a DeepWiki lookup. Read the most recent messages in
> **the one conversation you still have not caught up on**, oldest to newest, and *retain the full
> array of message views returned for later use*. Use the AI-grounded repository question tool to
> ask about 'apache/cassandra' the question "What is this project for, and what's its primary
> programming language?" and *keep the free-text answer returned*. Mark every message in **the one
> conversation you still have not caught up on** as read by you. Post a message to **the one
> conversation you still have not caught up on** whose body reproduces the sender and text for each
> message *from the retained read* so the thread clearly shows their contents. Reply in thread to the
> message about someone confirm its license with the full free-text answer you received from the
> repository query. Reply in thread to the message you posted earlier with the exact offer text
> saying you are happy to run DeepWiki on any other repos on the checklist and asking which ones to
> process, and report back in that same conversation that the steps are complete.

Three things are wrong with it, and they are separable.

## 1. The description is a substitution token, not a reference

**Bold** above: the same description four times. This is not L3's doing. v1 named `c_002` three
times — it is the explicit rung, so it names the id at every occurrence — and v1 also said "in
that chat" once. v2's instruction was *"replacing every identifier with the description supplied
for that entity"*, and it obliged literally: three ids became three phrases, and the one anaphor
became a fourth. **v2 went backwards on naturalness**, expanding a pronoun v1 had already used.
L3 then inherited all four.

Systemic, not a t1 quirk: across the twelve tasks, **40 of 81 phrase uses are repeats**. t8 pastes
one description five times.

And in t1 it is worse than clumsy. The description is `chat_only_with_unread` — *the one
conversation you still have not caught up on* — and the task's third step marks that conversation
read. **The third and fourth uses are false.** An agent resolving references lazily, as it works,
hits a description that no longer matches anything.

## 2. It is a step list wearing prose

Every action gets its own clause, in plan order, and the data flow is narrated out loud — *italic*
above: "retain the full array of message views returned for later use", "keep the free-text answer
returned", "from the retained read". The first sentence is a goal, and then the goal is followed by
the sequence it was supposed to replace.

The two steps the user singled out are one thing a person would ask for. "Read the recent messages
and retain the array" followed by "post a message whose body reproduces the sender and text for each
message from the retained read" is: *post a rundown of who said what*. The read is implied by the
outcome and does not need saying.

## 3. Content is dictated

`ask about 'apache/cassandra' the question "What is this project for, and what's its primary
programming language?"` hands over the exact question. A person says what they want to find out.
The repository **name** has to survive — that is what the expected answer is keyed to — but the
question around it does not, which is precisely why the judge specification must be restated at this
rung.

## The target

Hand-written, by me, as the thing Stage 11's instruction is aiming at — not model output. It exists
so the instruction can be judged before an authoring run is paid for. `check_l4_target.py` puts it
through the same checks the stage applies.

> There's one conversation I still haven't caught up on — could you clear my unread there and bring
> the rest of us up to speed while you're at it? Post a rundown into it of who said what in the
> recent traffic, so anyone skimming can see it without scrolling back. Someone in there asked for a
> repo's licence to be confirmed, in the message about someone confirm its license — find out what
> apache/cassandra is actually for and what it's mostly written in, and put that under their
> question. Round it off by following up on your own rundown, offering to run the same check over any
> other repos on the checklist and asking which ones they want done.

Three writes, as the plan has: the rundown, the reply under the licence question, the follow-up.
`mark_read` is "clear my unread there". Both reads are implied by outcomes rather than asked for.

### The judge items, restated for it

| | L1 as shipped | restated for L4 |
| --- | --- | --- |
| `carry:c0a1:text` hint | "Look at the text of the message created by the **send_message** call in **step 4** (the message posted to chat **c_002**)." | "the rundown of who said what, posted into the conversation being caught up on" |
| `carry:c1a1:text` hint | "Look at the text of the reply created by the **reply_to** call in **step 5** (the threaded reply to **m_004**)." | "the reply posted underneath the message that asked for the licence to be confirmed" |

The shipped hints name a tool, a step number and an entity id each — three things an L3 or L4 prompt
does not contain. They were handed to the grader unchanged at every level.

## What the checks say

```text
                        pre-fix L3 as shipped              the L4 target
prompt                  description pasted 4 times         (no complaints)
carry:c0a1:text         names 'c_002', names               clean
                        'send_message', refers to a
                        step by number
carry:c1a1:text         names 'm_004', names 'reply_to',   clean
                        refers to a step by number
```

## The limit of this, stated honestly

The target uses the chat's description **zero** times — "there's one conversation I still haven't
caught up on" is the same predicate in natural English, not the assigned phrase. At L4 that is
allowed on purpose, because requiring the phrase verbatim is what produced defect 1. But **nothing
verifies that a paraphrase still picks out one entity.** The repeat check catches over-use; the
zero-use check is therefore on at L2 and L3 and off at L4.

So L4 trades a checkable guarantee for naturalness. That is the deferred ambiguity check arriving,
and this is where it bites first: the honest version of L4 needs a resolution check — hand a model
the workspace and the prompt, ask which entity each reference denotes, compare against the plan's
targets. Until that exists, L4's references are asserted, not proved.
