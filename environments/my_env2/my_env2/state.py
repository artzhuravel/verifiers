"""Schema for the mock chat app: the entities plus the per-rollout state container.

Shared by the tools (which read/mutate it), the taskset (which seeds it and scores
against it), and the generator (which simulates over it). `ChatState` is a `vf.State`,
so it is the live per-rollout state, seeded per task in `Task.setup`. The seeded
workspace itself is built by `world.build_world`.
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
