"""ChatAdapter — everything about this environment that the generic pipeline needs.

The pipeline itself is env-agnostic: Stage 1 reads only the spec, and the authoring stages
read only the spec's English. Four things cannot be expressed that way, and they all live
here:

- **executing an action** against a state, given already-concrete args (replay);
- **naming what an action produced**, so a symbol can be bound to a real id;
- **comparing two states** as a set of id/structure facts (`signature`), which is the
  deterministic reward;
- **resolving a reference mode**, so "the chat where X came up" can be checked for
  uniqueness at authoring time instead of hoped about.

There is no `initial_state` here. In this pipeline the world is authored per task to satisfy
a sequence (see `seed.py`), not sampled from a fixed cast.
"""

import json
from collections import Counter
from typing import Any

import verifiers.v1 as vf
from verifiers.v1.mcp.server import _call_state

from my_env2.servers.tool import ChatToolset
from my_env2.state import ChatState, Message


class ChatAdapter:
    def __init__(self) -> None:
        self._tools = ChatToolset(vf.ToolsetConfig())

    # --- execution ------------------------------------------------------------------

    def execute(self, action: str, args: dict, state: ChatState) -> Any:
        """Run one action with fully concrete args, through the real tool.

        The tool is driven over `state` via the state contextvar, exactly as the eval-time
        channel does, so replay's effects and minted ids match production byte for byte.
        """
        token = _call_state.set(state)
        try:
            return getattr(self._tools, action)(**args)
        finally:
            _call_state.reset(token)

    def is_error(self, result: Any) -> bool:
        return isinstance(result, dict) and "error" in result

    def created(self, action: str, args: dict, result: Any) -> str | None:
        """The id of the entity an action brought into being, or None if it created nothing.

        Distinct from "the entity it affected": binding a symbol to an id is only correct for
        entities the rollout creates, and crediting `add_reaction` with the message it
        reacted to would bind a symbol that already had an id.
        """
        if action in ("send_message", "reply_to", "create_chat"):
            return result.get("id")
        return None

    def observed(self, action: str, result: Any) -> str | None:
        """What a read actually returned, as text a judge requirement can be written against.

        A scalar read has one nameable value (a handle); a collection read has none, so the
        whole result is handed over and the authoring pass decides which part of it a message
        would have to carry. External reads return None: their answer is not observable here.
        """
        if action == "get_user":
            return result.get("handle")
        if action in ("list_chats", "read_messages"):
            return json.dumps(result, ensure_ascii=False)
        return None

    def objects_of_type(self, state: ChatState, entity_type: str) -> list[str]:
        if entity_type == "chat":
            return list(state.chats)
        if entity_type == "message":
            return [message.id for message in state.messages]
        if entity_type == "user":
            return list(state.users)
        return []

    # --- comparison -----------------------------------------------------------------

    def _comparison_keys(self, state: ChatState, seed: ChatState) -> dict:
        """How each entity is named when two states are compared.

        Entities present in `seed` keep their real id — those are stable and mean the same
        thing in every trajectory. Entities *created during the rollout* are keyed by what
        they are (a chat by its members; a message by its chat, sender and parent) plus an
        occurrence index. A minted id is an artifact of a counter: an agent that creates one
        extra entity shifts every later id, and id-based comparison would then score correct
        work against structurally unrelated entities.
        """
        seeded_chats = set(seed.chats)
        seeded_messages = {message.id for message in seed.messages}
        keys: dict[str, object] = {}
        seen: Counter = Counter()
        # Chats first, in creation order, so a message into a new chat can name it.
        for chat_id in sorted(state.chats, key=lambda cid: int(cid.rsplit("_", 1)[-1])):
            if chat_id in seeded_chats:
                keys[chat_id] = chat_id
                continue
            shape = ("new_chat", tuple(sorted(state.chats[chat_id].member_ids)))
            seen[shape] += 1
            keys[chat_id] = (*shape, seen[shape])
        for message in sorted(state.messages, key=lambda m: m.ts):
            if message.id in seeded_messages:
                keys[message.id] = message.id
                continue
            shape = (
                "new_msg",
                keys.get(message.chat_id, message.chat_id),
                message.sender_id,
                keys.get(message.reply_to, message.reply_to),
            )
            seen[shape] += 1
            keys[message.id] = (*shape, seen[shape])
        return keys

    def signature(self, state: ChatState, seed: ChatState) -> set:
        """Id/structure facts about the state — content (text/emoji/name) excluded.

        A created entity contributes exactly one fact: its key already encodes both that it
        exists and how it is structured, so re-emitting membership / placement would count the
        same thing several times and over-weight whichever entity has more members. Facts
        about *seeded* entities stay id-keyed and itemised, since those are the ones an action
        can change after the fact (a reaction, a read).

        Excluding content is what makes the two-pass authoring affordable: Stage 7 fills in
        every free-text placeholder *after* Stage 6 has computed the expected state, and none
        of it can invalidate what was computed.
        """
        keys = self._comparison_keys(state, seed)
        seeded_chats = set(seed.chats)
        seeded_messages = {message.id for message in seed.messages}
        facts: set = set()
        for chat in state.chats.values():
            key = keys[chat.id]
            if chat.id not in seeded_chats:
                facts.add(key)  # existence + membership, in one fact
                continue
            facts.add(("chat", key))
            for user_id in chat.member_ids:
                facts.add(("member", key, user_id))
        for message in state.messages:
            key = keys[message.id]
            new = message.id not in seeded_messages
            if new:
                facts.add(key)  # existence + chat + sender + parent, in one fact
            else:
                facts.add(("msg", key))
                # Where a message landed is structure, not content: without these, posting to
                # the wrong chat or replying to the wrong parent would score the same as
                # getting it right.
                facts.add(("in", key, keys.get(message.chat_id, message.chat_id)))
                if message.reply_to:
                    facts.add(
                        ("replyto", key, keys.get(message.reply_to, message.reply_to))
                    )
            for reactors in message.reactions.values():
                for user_id in reactors:
                    facts.add(("react", key, user_id))  # emoji excluded (content)
            for user_id in message.read_by:
                # A new message is auto-read by its sender; that is implied by its key, not a
                # separate thing the agent achieved.
                if new and user_id == message.sender_id:
                    continue
                facts.add(("read", key, user_id))
        return facts

    # --- description --------------------------------------------------------------

    def describe(self, state: ChatState, entity_id: str) -> str:
        """One line about an entity, for an authoring prompt that has to talk about it."""
        if entity_id in state.chats:
            chat = state.chats[entity_id]
            label = f"'{chat.name}'" if chat.name else "(unnamed dm)"
            members = ", ".join(
                f"{state.users[m].name} @{state.users[m].handle}"
                for m in chat.member_ids
                if m in state.users
            )
            return f"{chat.kind} {label} — members: {members}"
        if entity_id in state.users:
            user = state.users[entity_id]
            return f"{user.name} @{user.handle}"
        message = next((m for m in state.messages if m.id == entity_id), None)
        if message is None:
            return entity_id
        sender = state.users.get(message.sender_id)
        where = state.chats.get(message.chat_id)
        parent = f", replying to {message.reply_to}" if message.reply_to else ""
        unread = "" if state.me in message.read_by else ", unread by you"
        return (
            f"in {where.name or message.chat_id if where else message.chat_id} "
            f"from {sender.name if sender else message.sender_id}{parent}{unread}: "
            f"{message.text!r}"
        )

    def giveaways(self, state: ChatState, entity_id: str) -> set[str]:
        """Strings that identify an entity outright, without anyone having to work it out.

        A de-scaffolded prompt must not contain these for an entity it is supposed to describe.
        Dropping the ids is not enough on its own: a prompt that says "Alice Rivera (the author of
        the message about the feature freeze)" has replaced a description with an annotated name
        and handed back the resolution step the description existed to create.
        """
        if entity_id in state.users:
            user = state.users[entity_id]
            return {user.name, user.handle}
        if entity_id in state.chats and state.chats[entity_id].name:
            return {state.chats[entity_id].name}
        return set()

    # --- reference modes ----------------------------------------------------------

    def resolve(self, state: ChatState, mode_id: str, params: dict) -> list[str]:
        """Every entity satisfying a reference mode. A mode is usable for one entity only
        when this returns exactly that entity (see the spec's `reference_mode_semantics`).

        Modes that name a superlative ("the most X") return a result only when the maximum is
        strict: a tie means no entity satisfies "more than any other", and silently picking a
        winner would hand the agent an unresolvable description.
        """
        resolver = getattr(self, f"_mode_{mode_id}", None)
        if resolver is None:
            raise KeyError(f"adapter implements no reference mode {mode_id!r}")
        return resolver(state, **params)

    # user modes

    def _mode_user_by_handle(self, state: ChatState, handle: str) -> list[str]:
        return [u.id for u in state.users.values() if u.handle == handle.lstrip("@")]

    def _mode_user_by_display_name(self, state: ChatState, name: str) -> list[str]:
        return [u.id for u in state.users.values() if u.name == name]

    def _mode_user_authored_text(self, state: ChatState, text: str) -> list[str]:
        return _unique(m.sender_id for m in _matching(state, text))

    def _mode_user_most_messages(self, state: ChatState) -> list[str]:
        return _strict_max(Counter(m.sender_id for m in state.messages))

    # chat modes

    def _mode_chat_by_name(self, state: ChatState, name: str) -> list[str]:
        # A DM has no name, and every DM would otherwise satisfy `name=None` — which reads back
        # out of `phrase` as "the None channel".
        return [c.id for c in state.chats.values() if name and c.name == name]

    def _mode_chat_by_member_count(self, state: ChatState, count: int) -> list[str]:
        return [c.id for c in state.chats.values() if len(c.member_ids) == int(count)]

    def _mode_chat_containing_text(self, state: ChatState, text: str) -> list[str]:
        return _unique(m.chat_id for m in _matching(state, text))

    def _mode_chat_only_with_unread(self, state: ChatState) -> list[str]:
        return _unique(m.chat_id for m in state.messages if state.me not in m.read_by)

    # message modes

    def _mode_message_by_text(self, state: ChatState, text: str) -> list[str]:
        return [m.id for m in _matching(state, text)]

    def _mode_message_reply_to_text(self, state: ChatState, text: str) -> list[str]:
        parents = {m.id for m in _matching(state, text)}
        return [m.id for m in state.messages if m.reply_to in parents]

    def _mode_message_most_reacted(self, state: ChatState) -> list[str]:
        return _strict_max(
            Counter(
                {
                    m.id: len(
                        {user for users in m.reactions.values() for user in users}
                    )
                    for m in state.messages
                }
            )
        )

    def _mode_message_newest_by_handle(
        self, state: ChatState, handle: str
    ) -> list[str]:
        authors = self._mode_user_by_handle(state, handle)
        if len(authors) != 1:
            return []
        theirs = [m for m in state.messages if m.sender_id == authors[0]]
        return [max(theirs, key=lambda m: m.ts).id] if theirs else []

    # --- deterministic fallback for reference-mode params -------------------------

    def mode_params(
        self, state: ChatState, mode_id: str, entity_id: str
    ) -> dict | None:
        """Params that make `mode_id` pick out `entity_id`, or None if this mode cannot.

        The authoring model chooses which mode suits an entity, but it is not the thing that
        makes the choice *work*: a phrase it invents may match two entities or none. This
        derives the params from the state instead, so every entity ends up with a reference
        that provably resolves. Where a mode needs a distinctive phrase, the shortest span of
        the real text that occurs exactly once is used — a longer one is no more unique and
        quotes more of the message back at the agent than it has to.

        The return is verified before it is handed back, so a non-None result *is* a resolution
        and a caller need not re-check it. Deriving without verifying was not enough: a
        superlative mode has no params to get wrong and so would claim to fit any entity, and a
        display name derived from the target may well be shared with someone else.
        """
        params = self._derive(state, mode_id, entity_id)
        if params is None or self.resolve(state, mode_id, params) != [entity_id]:
            return None
        return params

    def _derive(self, state: ChatState, mode_id: str, entity_id: str) -> dict | None:
        if mode_id == "user_by_handle":
            user = state.users.get(entity_id)
            return {"handle": user.handle} if user else None
        if mode_id == "user_by_display_name":
            user = state.users.get(entity_id)
            return {"name": user.name} if user else None
        if mode_id == "user_authored_text":
            theirs = [m for m in state.messages if m.sender_id == entity_id]
            return _first(
                {"text": phrase}
                for message in theirs
                for phrase in [self._distinctive(state, message)]
                if phrase
            )
        if mode_id == "user_most_messages":
            return {}
        if mode_id == "chat_by_name":
            chat = state.chats.get(entity_id)
            return {"name": chat.name} if chat and chat.name else None
        if mode_id == "chat_by_member_count":
            chat = state.chats.get(entity_id)
            return {"count": len(chat.member_ids)} if chat else None
        if mode_id == "chat_containing_text":
            return _first(
                {"text": phrase}
                for message in state.messages
                if message.chat_id == entity_id
                for phrase in [self._distinctive(state, message)]
                if phrase
            )
        if mode_id == "chat_only_with_unread":
            return {}
        if mode_id == "message_by_text":
            message = _find(state, entity_id)
            phrase = self._distinctive(state, message) if message else None
            return {"text": phrase} if phrase else None
        if mode_id == "message_reply_to_text":
            message = _find(state, entity_id)
            parent = (
                _find(state, message.reply_to) if message and message.reply_to else None
            )
            phrase = self._distinctive(state, parent) if parent else None
            return {"text": phrase} if phrase else None
        if mode_id == "message_most_reacted":
            return {}
        if mode_id == "message_newest_by_handle":
            message = _find(state, entity_id)
            sender = state.users.get(message.sender_id) if message else None
            return {"handle": sender.handle} if sender else None
        raise KeyError(f"adapter derives no params for reference mode {mode_id!r}")

    def _distinctive(self, state: ChatState, message: Message) -> str | None:
        """A short span of words in `message` that appears in no other message.

        "Shortest" is not the goal on its own. Any span containing a unique span is itself
        unique, so the shortest unique span is a single word whenever one exists — and "the
        message about Before" is a worse reference than "the message about the backfill job",
        however much less it quotes. So: two words up, and within a width, a span carrying a real
        word before one made of nothing but short ones. One word only for a one-word message,
        which otherwise gets no text-based reference at all.
        """
        words = message.text.split()
        candidates = [
            words[start : start + width]
            for width in range(1, min(len(words), _PHRASE_CAP) + 1)
            for start in range(len(words) - width + 1)
        ]
        for span in sorted(candidates, key=_phrase_rank):
            phrase = " ".join(span).strip(_TRAILING)
            if len(phrase) >= 3 and len(_matching(state, phrase)) == 1:
                return phrase
        return None


_PHRASE_CAP = 8
_PHRASE_TARGET = 4
_TRAILING = ".,:;!?\"'"


def _phrase_rank(span: list[str]) -> tuple:
    """How well a span of words would read as "the message about ___".

    The shortest unique span is the wrong thing to want. Any span containing a unique one is
    itself unique, so the shortest is usually a single word — and "the message about Before" is a
    worse handle than "the message about the backfill job times out", however much less it
    quotes. Three things decide it instead: don't run across a sentence boundary, which produces
    a phrase nobody would say; open on a real word rather than a preposition or an article; and
    sit near four words, which is about the length at which a quote reads as a topic.
    """
    return (
        any(word.rstrip(_TRAILING) != word for word in span[:-1]),
        any(not word.strip(_TRAILING + "-–—()[]") for word in span),
        len(span[0].strip(_TRAILING)) < 5,
        abs(len(span) - _PHRASE_TARGET),
    )


def _find(state: ChatState, message_id: str | None) -> Message | None:
    return next((m for m in state.messages if m.id == message_id), None)


def _first(candidates):
    return next(iter(candidates), None)


def _matching(state: ChatState, text: str):
    needle = text.strip().casefold()
    return [m for m in state.messages if needle and needle in m.text.casefold()]


def _unique(ids) -> list[str]:
    """Deduplicated, order preserved — several matching messages may share one author."""
    return list(dict.fromkeys(ids))


def _strict_max(counts: Counter) -> list[str]:
    if not counts:
        return []
    top = max(counts.values())
    if top == 0:
        return []
    leaders = [key for key, count in counts.items() if count == top]
    return leaders if len(leaders) == 1 else []
