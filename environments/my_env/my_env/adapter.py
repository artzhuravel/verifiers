"""ChatAdapter: the my_env implementation of the generator's env seam (see generate.py).

Wraps the real `ChatToolset` over an in-memory `ChatState`: it owns seeding, enumerates
objects by type, mints a permanently-invalid ref, and applies an action by assembling
full args (placing the object id and filling value args), running the tool, and
reporting the created/affected entity id.
"""

import json
from collections import Counter
from random import Random

import verifiers.v1 as vf
from verifiers.v1.mcp.server import _call_state

from my_env.generate import Outcome
from my_env.servers.tool import ChatToolset
from my_env.state import ChatState
from my_env.world import build_world

_BAD = {"chat": "c_missing", "message": "m_missing", "user": "u_missing"}


def _placeholder(param: str) -> str:
    """A value arg the generator has no business choosing.

    Content — a message body, a reaction, a chat's name — belongs to the authoring step, not
    to sampling. Filling these with plausible-looking strings ("sounds good", ":tada:") was
    actively harmful: the authoring model cannot tell a sampled filler from a requirement, so
    it treated the wording as fixed and inherited its tone. A self-describing sentinel makes
    the emptiness explicit instead. None of these reach the reward — `signature` excludes
    text, emoji and names by design.
    """
    return f"<{param}>"


class ChatAdapter:
    def __init__(self) -> None:
        self._tools = ChatToolset(vf.ToolsetConfig())

    def initial_state(self, rng: Random) -> ChatState:
        return build_world(rng)

    def objects_of_type(self, state: ChatState, entity_type: str) -> list[str]:
        if entity_type == "chat":
            return list(state.chats)
        if entity_type == "message":
            return [m.id for m in state.messages]
        if entity_type == "user":
            return list(state.users)
        return []

    def invalid_ref(self, entity_type: str) -> str:
        return _BAD[entity_type]

    def is_error(self, result) -> bool:
        # This env signals failure as a JSON dict with an "error" key. Not used by the
        # active reward; kept as the building block for a future invalid-attempt trace pass.
        if not isinstance(result, str):
            return False
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            return '"error"' in result
        return isinstance(parsed, dict) and "error" in parsed

    def _comparison_keys(self, state: ChatState, seed: ChatState) -> dict:
        """How each entity is named when two states are compared.

        Entities present in `seed` keep their real id — those are stable and mean the same
        thing in every trajectory. Entities *created during the rollout* are keyed by what
        they are (a chat by its members; a message by its chat, sender and parent) plus an
        occurrence index. A minted id is an artifact of a counter: an agent that creates
        one extra entity shifts every later id, and id-based comparison would then score
        correct work against structurally unrelated entities.
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
        exists and how it is structured, so re-emitting membership / placement would count
        the same thing several times and over-weight whichever entity has more members.
        Facts about *seeded* entities stay id-keyed and itemised, since those are the ones
        an action can change after the fact (a reaction, a read).
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
                # Where a message landed is structure, not content: without these, posting
                # to the wrong chat or replying to the wrong parent would score the same as
                # getting it right.
                facts.add(("in", key, keys.get(message.chat_id, message.chat_id)))
                if message.reply_to:
                    facts.add(("replyto", key, keys.get(message.reply_to, message.reply_to)))
            for reactors in message.reactions.values():
                for user_id in reactors:
                    facts.add(("react", key, user_id))  # emoji excluded (content)
            for user_id in message.read_by:
                # A new message is auto-read by its sender; that is implied by its key, not
                # a separate thing the agent achieved.
                if new and user_id == message.sender_id:
                    continue
                facts.add(("read", key, user_id))
        return facts

    def apply(self, action: str, object_id: str | None, state: ChatState, rng: Random) -> Outcome:
        args = self._args(action, object_id, state, rng)
        # Run the real tool over `state` through the state contextvar, exactly as the
        # eval-time channel does — so effects and ids match production.
        token = _call_state.set(state)
        try:
            result = getattr(self._tools, action)(**args)
        finally:
            _call_state.reset(token)
        error = isinstance(result, dict) and "error" in result
        entity_id = None if error else self._entity_id(action, args, result)
        value = None if error else self._value(action, result)
        return Outcome(error=error, entity_id=entity_id, args=args, value=value)

    def _args(self, action: str, object_id: str | None, state: ChatState, rng: Random) -> dict:
        if action == "list_chats":
            return {}
        if action == "read_messages":
            return {"chat_id": object_id}
        if action == "get_user":
            return {"user_id": object_id}
        if action == "mark_read":
            return {"chat_id": object_id}
        if action == "send_message":
            return {"chat_id": object_id, "text": _placeholder("text")}
        if action == "reply_to":
            return {"message_id": object_id, "text": _placeholder("text")}
        if action == "add_reaction":
            return {"message_id": object_id, "emoji": _placeholder("emoji")}
        # create_chat has no single object; pick valid members, and sometimes name the chat —
        # whether it is named is structure (it decides dm vs group), what it is called is not.
        others = [u for u in state.users if u != state.me]
        members = rng.sample(others, rng.randint(1, min(2, len(others))))
        named = rng.random() < 0.5
        return {"member_ids": members, "name": _placeholder("name") if named else None}

    def _value(self, action: str, result) -> str | None:
        """The nameable result of a read, for the actions where there is exactly one. Only
        `get_user` qualifies: a handle is a single value an authored obligation can be about,
        whereas a chat's messages are a collection with no one value to point at."""
        if action == "get_user":
            return result.get("handle")
        return None

    def _entity_id(self, action: str, args: dict, result) -> str | None:
        if action in ("send_message", "reply_to", "create_chat"):
            return result.get("id")  # newly created entity
        if action == "add_reaction":
            return args["message_id"]  # affected message
        if action == "mark_read":
            return args["chat_id"]  # affected chat
        return None  # reads
