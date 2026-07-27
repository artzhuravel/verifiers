"""Chat tools over per-rollout state.

The toolset is parameterized with `ChatState`, so the framework syncs `self.state`
through the rollout's state channel: each call pulls the current state, the tool
reads/mutates it, and the result is pushed back. The task seeds the initial
conversation in `Task.setup` (see `taskset.py`), and the reward reads the final
`trace.state`. Writes therefore stay isolated per rollout.
"""

import verifiers.v1 as vf

from my_env.state import Chat, ChatState, Message


class ChatToolset(vf.Toolset[vf.ToolsetConfig, ChatState]):
    TOOL_PREFIX = "chat"

    # --- read tools ---

    @vf.tool
    def list_chats(self) -> list[dict]:
        """List the chats the current user is a member of."""
        return [
            {"id": c.id, "kind": c.kind, "name": c.name or c.id, "members": c.member_ids}
            for c in self.state.chats.values()
            if self.state.me in c.member_ids
        ]

    @vf.tool
    def read_messages(self, chat_id: str, limit: int = 20) -> list[dict]:
        """Read the most recent messages in a chat, oldest to newest."""
        in_chat = [m for m in self.state.messages if m.chat_id == chat_id]
        return [self._render(m) for m in in_chat[-limit:]]

    @vf.tool
    def get_user(self, user_id: str) -> dict:
        """Look up a user by id."""
        user = self.state.users.get(user_id)
        if user is None:
            return {"error": "no such user"}
        return {"id": user.id, "name": user.name, "handle": user.handle}

    # --- write tools ---

    @vf.tool
    def send_message(self, chat_id: str, text: str) -> dict:
        """Send a message from the current user to a chat."""
        if chat_id not in self.state.chats:
            return {"error": "no such chat"}
        return self._append(chat_id, text)

    @vf.tool
    def reply_to(self, message_id: str, text: str) -> dict:
        """Reply to a message in its chat (threaded)."""
        parent = self._find(message_id)
        if parent is None:
            return {"error": "no such message"}
        return self._append(parent.chat_id, text, reply_to=message_id)

    @vf.tool
    def add_reaction(self, message_id: str, emoji: str) -> dict:
        """Add an emoji reaction from the current user to a message."""
        message = self._find(message_id)
        if message is None:
            return {"error": "no such message"}
        reactors = message.reactions.setdefault(emoji, [])
        if self.state.me not in reactors:
            reactors.append(self.state.me)
        return self._render(message)

    @vf.tool
    def mark_read(self, chat_id: str) -> dict:
        """Mark every message in a chat as read by the current user."""
        marked = 0
        for message in self.state.messages:
            if message.chat_id == chat_id and self.state.me not in message.read_by:
                message.read_by.append(self.state.me)
                marked += 1
        return {"chat_id": chat_id, "marked_read": marked}

    @vf.tool
    def create_chat(self, member_ids: list[str], name: str | None = None) -> dict:
        """Create a new chat with the given members; the current user is always included."""
        members = list(dict.fromkeys([self.state.me, *member_ids]))
        kind = "group" if name or len(members) > 2 else "dm"
        chat_id = f"c_{self.state.next_chat_id:03d}"
        self.state.next_chat_id += 1
        self.state.chats[chat_id] = Chat(
            id=chat_id, kind=kind, name=name, member_ids=members
        )
        return {"id": chat_id, "kind": kind, "name": name, "members": members}

    # --- helpers (≥2 call sites) ---

    def _find(self, message_id: str) -> Message | None:
        return next((m for m in self.state.messages if m.id == message_id), None)

    def _append(self, chat_id: str, text: str, reply_to: str | None = None) -> dict:
        message = Message(
            id=f"m_{self.state.next_message_id:03d}",
            chat_id=chat_id,
            sender_id=self.state.me,
            text=text,
            ts=max((m.ts for m in self.state.messages), default=0) + 1,
            reply_to=reply_to,
            read_by=[self.state.me],
        )
        self.state.messages.append(message)
        self.state.next_message_id += 1
        return self._render(message)

    def _render(self, message: Message) -> dict:
        return {
            "id": message.id,
            "chat_id": message.chat_id,
            "from": self.state.users[message.sender_id].name,
            "text": message.text,
            "ts": message.ts,
            "reply_to": message.reply_to,
            "reactions": message.reactions,
            "read_by": message.read_by,
        }


if __name__ == "__main__":
    ChatToolset.run()
