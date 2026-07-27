"""ChatAdapter: the my_env implementation of the generator's env seam (see generate.py).

Wraps the real `ChatToolset` over an in-memory `ChatState`: it owns seeding, enumerates
objects by type, mints a permanently-invalid ref, and applies an action by assembling
full args (placing the object id and filling value args), running the tool, and
reporting the created/affected entity id.
"""

import json
from random import Random

import verifiers.v1 as vf
from verifiers.v1.mcp.server import _call_state

from my_env.generate import Outcome
from my_env.servers.tool import ChatToolset
from my_env.state import ChatState
from my_env.world import build_world

_TEXTS = ["on my way", "sounds good", "running late", "let's sync tomorrow", "shipping it"]
_EMOJIS = [":+1:", ":tada:", ":eyes:", ":heart:"]
_CHAT_NAMES = ["standup", "retro", "offsite", "triage"]
"""Names for chats the agent is asked to *create* — kept disjoint from the seeded chat
names so a created chat is never confused with a pre-existing one."""
_BAD = {"chat": "c_missing", "message": "m_missing", "user": "u_missing"}


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

    def signature(self, state: ChatState) -> set:
        """Id/structure facts about the state — content (text/emoji/name) excluded."""
        facts: set = set()
        for chat in state.chats.values():
            facts.add(("chat", chat.id))
            for user_id in chat.member_ids:
                facts.add(("member", chat.id, user_id))
        for message in state.messages:
            facts.add(("msg", message.id))
            # Where a message landed is structure, not content: without these two, sending
            # to the wrong chat or replying to the wrong parent scores the same as getting
            # it right, and the referential difficulty of a prompt goes unmeasured.
            facts.add(("in", message.id, message.chat_id))
            if message.reply_to:
                facts.add(("replyto", message.id, message.reply_to))
            for reactors in message.reactions.values():
                for user_id in reactors:
                    facts.add(("react", message.id, user_id))  # emoji excluded (content)
            for user_id in message.read_by:
                facts.add(("read", message.id, user_id))
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
        return Outcome(error=error, entity_id=entity_id, args=args)

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
            return {"chat_id": object_id, "text": rng.choice(_TEXTS)}
        if action == "reply_to":
            return {"message_id": object_id, "text": rng.choice(_TEXTS)}
        if action == "add_reaction":
            return {"message_id": object_id, "emoji": rng.choice(_EMOJIS)}
        # create_chat has no single object; pick valid members and maybe a name.
        others = [u for u in state.users if u != state.me]
        members = rng.sample(others, rng.randint(1, min(2, len(others))))
        return {"member_ids": members, "name": rng.choice(_CHAT_NAMES) if rng.random() < 0.5 else None}

    def _entity_id(self, action: str, args: dict, result) -> str | None:
        if action in ("send_message", "reply_to", "create_chat"):
            return result.get("id")  # newly created entity
        if action == "add_reaction":
            return args["message_id"]  # affected message
        if action == "mark_read":
            return args["chat_id"]  # affected chat
        return None  # reads
