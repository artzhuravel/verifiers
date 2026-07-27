"""Schema for the mock chat app: the entities plus the per-rollout state container.

Shared by the tools (which read/mutate it) and the taskset (which seeds it and
scores against it). `ChatState` is a `vf.State`, so once per-task seeding is wired
(step 2) it becomes the live per-rollout state; step 1 just seeds it statically
via the `SAMPLE` constant below.
"""

from typing import Literal

from pydantic import BaseModel, Field

import verifiers.v1 as vf


class User(BaseModel):
    id: str
    name: str
    handle: str = ""


class Message(BaseModel):
    id: str
    chat_id: str
    sender_id: str
    text: str
    # A logical sequence number, not a wall-clock time — keeps ordering and seeds
    # reproducible.
    ts: int
    reply_to: str | None = None
    # emoji -> user ids who reacted with it
    reactions: dict[str, list[str]] = Field(default_factory=dict)
    read_by: list[str] = Field(default_factory=list)


class Chat(BaseModel):
    id: str
    kind: Literal["dm", "group"]
    name: str | None = None
    member_ids: list[str] = Field(default_factory=list)


class ChatState(vf.State):
    # The acting user's id (session context, not an entity) — tools like "my chats"
    # or "messages mentioning me" need to know whose account this is.
    me: str = ""
    users: dict[str, User] = Field(default_factory=dict)
    chats: dict[str, Chat] = Field(default_factory=dict)
    # A single chronologically ordered list; tools filter by chat_id.
    messages: list[Message] = Field(default_factory=list)
    # Monotonic id counters so entity ids are a deterministic function of creation
    # order (not of collection size), independent of deletions or seeded id names.
    next_message_id: int = 1
    next_chat_id: int = 1


# A tiny fixed conversation for step 1. Replaced by per-task seeding in step 2.
SAMPLE = ChatState(
    me="u_me",
    users={
        "u_me": User(id="u_me", name="You", handle="you"),
        "u_alice": User(id="u_alice", name="Alice", handle="alice"),
        "u_bob": User(id="u_bob", name="Bob", handle="bob"),
    },
    chats={
        "c_launch": Chat(
            id="c_launch",
            kind="group",
            name="launch",
            member_ids=["u_me", "u_alice", "u_bob"],
        ),
        "c_alice": Chat(id="c_alice", kind="dm", member_ids=["u_me", "u_alice"]),
    },
    messages=[
        Message(id="m_001", chat_id="c_launch", sender_id="u_alice", text="kickoff at 3pm?", ts=1),
        Message(id="m_002", chat_id="c_launch", sender_id="u_bob", text="works for me", ts=2),
        Message(id="m_003", chat_id="c_launch", sender_id="u_alice", text="great, see you then", ts=3),
        Message(id="m_004", chat_id="c_alice", sender_id="u_alice", text="can you review the deck?", ts=4),
    ],
    next_message_id=5,
    next_chat_id=3,
)
