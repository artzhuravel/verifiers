"""Turning an authored world into a seed state, and binding symbols to real ids.

Stage 3 hands back a *draft*: people, conversations and history invented to satisfy the
sequence, referring to each other by local keys it made up (`"u1"`, `"c2"`). Stage 5 adds more
of the same as filler. This module is what turns either into a `ChatState` with real ids, and
it is the only place that decides what a real id looks like.

It validates rather than repairs. A draft that names a sender it never declared, threads a
reply under a message in another chat, or leaves a manifest symbol unbound is rejected whole —
the retry policy above it can afford another call, and quietly patching a draft would leave a
task whose prompt describes a world that is not the one built.

Two invariants are enforced here rather than asked for, because asking is unreliable and both
are load-bearing:

- **The acting user is a member of every chat.** `list_chats` shows only the actor's chats, so
  a chat the actor is not in is invisible — and an invisible entity cannot be referred to,
  resolved, or acted on.
- **The acting user has no seeded reactions.** A seeded reaction by the actor would make a
  task's own `add_reaction` write a fact that is already true.
"""

import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from my_env2.state import Chat, ChatState, Message, User

ME = "u_me"
ACTOR_HANDLE = "you"
"""The acting user's handle is reserved, not authored.

Letting the model choose one produced the same failure over and over: it would pick a handle for
itself and then declare a colleague with the same one, because it reads `users` as "everyone,
including me". Reserving a handle removes the collision instead of asking for it not to happen.
The display name is still authored — a named actor is what makes the world read as somebody's."""


class DraftError(ValueError):
    """The authored world does not describe a buildable, sequence-satisfying seed."""


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _drop_nulls(cls, data):
        """A null from the model means "not applicable", so let the default stand.

        Writing out every optional key with `null` is what a model does when it is following a
        schema conscientiously — `"reaction_emoji": null` on a message nobody reacted to. Treating
        that as a type error spends a correction round on a reply that was never actually wrong.
        """
        if not isinstance(data, dict):
            return data
        return {key: value for key, value in data.items() if value is not None}


class DraftUser(_Model):
    ref: str
    """The local key the authoring model refers to this person by elsewhere in the draft."""
    name: str
    handle: str
    symbol: str | None = None
    """The manifest placeholder this person instantiates, if any."""


class DraftChat(_Model):
    ref: str
    members: list[str] = Field(default_factory=list)
    """Local user keys. The acting user is added automatically."""
    name: str | None = None
    symbol: str | None = None


class DraftMessage(_Model):
    ref: str
    chat: str
    sender: str
    """A local user key, or "actor" for the acting user."""
    text: str
    reply_to: str | None = None
    read_by_actor: bool = True
    reactors: list[str] = Field(default_factory=list)
    reaction_emoji: str = ":+1:"
    symbol: str | None = None
    order: int = 0
    """Where this sits on the workspace's one shared clock. It exists so that filler history
    can be *interleaved* with the core history rather than appended after it — otherwise every
    recent message in the world is filler, and "the latest thing they posted" always resolves
    into the padding."""


class WorldDraft(_Model):
    topic: str = ""
    actor_name: str = "You"
    users: list[DraftUser] = Field(default_factory=list)
    chats: list[DraftChat] = Field(default_factory=list)
    messages: list[DraftMessage] = Field(default_factory=list)


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", text.strip().casefold()).strip("_")
    return cleaned or "x"


def build(
    draft: WorldDraft, required: dict[str, str] | None = None
) -> tuple[ChatState, dict[str, str]]:
    """`(seed state, symbol -> real id)`.

    `required` maps every seed symbol the sequence needs to its entity type; when given, the
    draft must bind each one exactly once and to the right type.
    """
    users: dict[str, User] = {
        ME: User(id=ME, name=draft.actor_name, handle=ACTOR_HANDLE)
    }
    user_ids: dict[str, str] = {"actor": ME}
    binding: dict[str, str] = {}
    handles = {ACTOR_HANDLE}

    for entry in draft.users:
        if entry.ref in user_ids:
            raise DraftError(f"two people share the local key {entry.ref!r}")
        handle = entry.handle.lstrip("@") or _slug(entry.name)
        if handle in handles:
            # Handles are the one thing this environment promises never collide — it is what
            # makes a person nameable when display names do not. Renaming the duplicate would
            # honour the letter of that and produce a world nobody asked for, so a repeat is
            # rejected. Colliding with the acting user's own handle is the common case: it means
            # the draft invented a second copy of you.
            raise DraftError(
                f"{entry.ref!r} uses the handle {handle!r}, which is already taken"
                + (" — that is your own handle" if handle == ACTOR_HANDLE else "")
                + "; every handle must be different"
            )
        handles.add(handle)
        user_id = f"u_{_slug(handle)}"
        while user_id in users:
            user_id += "x"
        users[user_id] = User(id=user_id, name=entry.name, handle=handle)
        user_ids[entry.ref] = user_id
        _bind(binding, entry.symbol, user_id)

    chats: dict[str, Chat] = {}
    chat_ids: dict[str, str] = {}
    for index, entry in enumerate(draft.chats, start=1):
        if entry.ref in chat_ids:
            raise DraftError(f"two chats share the local key {entry.ref!r}")
        members = [ME]
        for ref in entry.members:
            if ref not in user_ids:
                raise DraftError(
                    f"chat {entry.ref!r} names an undeclared member {ref!r}"
                )
            if user_ids[ref] not in members:
                members.append(user_ids[ref])
        chat_id = f"c_{index:03d}"
        chats[chat_id] = Chat(
            id=chat_id,
            kind="group" if entry.name or len(members) > 2 else "dm",
            name=entry.name,
            member_ids=members,
        )
        chat_ids[entry.ref] = chat_id
        _bind(binding, entry.symbol, chat_id)

    messages: list[Message] = []
    message_ids: dict[str, str] = {}
    # The clock is `order`, with draft position breaking ties, so a reply must be authored
    # with an order at least its parent's — checked below rather than assumed.
    on_the_clock = sorted(
        enumerate(draft.messages), key=lambda pair: (pair[1].order, pair[0])
    )
    for index, (_, entry) in enumerate(on_the_clock, start=1):
        if entry.ref in message_ids:
            raise DraftError(f"two messages share the local key {entry.ref!r}")
        if entry.chat not in chat_ids:
            raise DraftError(
                f"message {entry.ref!r} is in undeclared chat {entry.chat!r}"
            )
        if entry.sender not in user_ids:
            raise DraftError(
                f"message {entry.ref!r} is from undeclared sender {entry.sender!r}"
            )
        chat_id = chat_ids[entry.chat]
        sender_id = user_ids[entry.sender]
        if sender_id not in chats[chat_id].member_ids:
            raise DraftError(
                f"message {entry.ref!r} is from {entry.sender!r}, who is not in {entry.chat!r}"
            )
        parent = None
        if entry.reply_to:
            if entry.reply_to not in message_ids:
                raise DraftError(
                    f"message {entry.ref!r} replies to {entry.reply_to!r}, which is not an "
                    "earlier message"
                )
            parent = message_ids[entry.reply_to]
            if next(m for m in messages if m.id == parent).chat_id != chat_id:
                raise DraftError(
                    f"message {entry.ref!r} replies across chats, which cannot happen"
                )
        read_by = [sender_id]
        if entry.read_by_actor and ME not in read_by:
            read_by.append(ME)
        # Reactions decide `message_most_reacted`, which needs a strict maximum, so a quietly
        # dropped reactor can turn an intended clear winner into a tie and cost the message its
        # reference. Undeclared and non-member reactors are therefore rejected, not skipped. The
        # actor is the one exception: the actor is removed rather than refused, because a seeded
        # reaction of theirs would make a task's own `add_reaction` write a fact already true,
        # and that is a rule the draft was never told about.
        reactors = []
        for ref in dict.fromkeys(entry.reactors):
            if ref not in user_ids:
                raise DraftError(
                    f"message {entry.ref!r} has a reaction from undeclared {ref!r}"
                )
            if user_ids[ref] == ME:
                continue
            if user_ids[ref] not in chats[chat_id].member_ids:
                raise DraftError(
                    f"message {entry.ref!r} has a reaction from {ref!r}, who is not in "
                    f"{entry.chat!r}"
                )
            reactors.append(user_ids[ref])
        message_id = f"m_{index:03d}"
        messages.append(
            Message(
                id=message_id,
                chat_id=chat_id,
                sender_id=sender_id,
                text=entry.text,
                ts=index,
                reply_to=parent,
                reactions={entry.reaction_emoji: reactors} if reactors else {},
                read_by=read_by,
            )
        )
        message_ids[entry.ref] = message_id
        _bind(binding, entry.symbol, message_id)

    state = ChatState(
        me=ME,
        users=users,
        chats=chats,
        messages=messages,
        next_message_id=len(messages) + 1,
        next_chat_id=len(chats) + 1,
    )
    if required is not None:
        _check_binding(state, binding, required)
    return state, binding


def _bind(binding: dict[str, str], symbol: str | None, entity_id: str) -> None:
    if not symbol:
        return
    if symbol in binding:
        raise DraftError(
            f"{symbol} is claimed by two entities ({binding[symbol]}, {entity_id})"
        )
    binding[symbol] = entity_id


def _check_binding(
    state: ChatState, binding: dict[str, str], required: dict[str, str]
) -> None:
    missing = sorted(set(required) - set(binding))
    if missing:
        raise DraftError(
            f"the sequence needs {', '.join(missing)}, which nothing instantiates"
        )
    extra = sorted(set(binding) - set(required))
    if extra:
        raise DraftError(
            f"claims placeholders the sequence never asked for: {', '.join(extra)}"
        )
    # Safe to merge because the three id spaces are disjoint by construction — `c_NNN`, `u_…`,
    # `m_NNN` — so no entry can shadow another.
    kinds = {
        **{chat_id: "chat" for chat_id in state.chats},
        **{user_id: "user" for user_id in state.users},
        **{message.id: "message" for message in state.messages},
    }
    for symbol, entity_type in required.items():
        if kinds[binding[symbol]] != entity_type:
            raise DraftError(
                f"{symbol} must be a {entity_type} but was bound to a "
                f"{kinds[binding[symbol]]} ({binding[symbol]})"
            )


def summarise(state: ChatState) -> str:
    """The world as an authoring prompt sees it: every entity, with its real id."""
    lines = [f"You act as {state.users[state.me].name} (id {state.me}).", "", "People:"]
    for user in state.users.values():
        lines.append(f"  {user.id}  {user.name} @{user.handle}")
    for chat in state.chats.values():
        members = ", ".join(
            f"{state.users[m].name} @{state.users[m].handle}"
            for m in chat.member_ids
            if m in state.users
        )
        lines.append(
            f"\n{chat.kind} {chat.name or '(dm)'} ({chat.id}) — members: {members}"
        )
        for message in (m for m in state.messages if m.chat_id == chat.id):
            marks = []
            if message.reply_to:
                marks.append(f"reply to {message.reply_to}")
            if state.me not in message.read_by:
                marks.append("UNREAD by you")
            for emoji, reactors in message.reactions.items():
                marks.append(f"{emoji} x{len(reactors)}")
            suffix = f"  ({'; '.join(marks)})" if marks else ""
            sender = state.users[message.sender_id]
            lines.append(
                f"  {message.id} [{sender.name} @{sender.handle}]: {message.text}{suffix}"
            )
    return "\n".join(lines)


def summarise_draft(draft: WorldDraft) -> str:
    """The world in the vocabulary a *draft* speaks: local keys, not real ids.

    Stage 5 adds to an existing draft, so this is what it has to be shown. Given the built state
    instead it would only ever see real ids, and every addition naming one would be rejected —
    leaving it structurally unable to put filler in an existing conversation, which is where
    filler has to go if it is to hide anything.
    """
    lines = [f"You are {draft.actor_name} @{ACTOR_HANDLE}, and a member of every chat."]
    lines.append("\nPeople (refer to them by the key on the left):")
    for user in draft.users:
        lines.append(f"  {user.ref:6} {user.name} @{user.handle.lstrip('@')}")
    for chat in draft.chats:
        members = ", ".join(chat.members)
        lines.append(
            f"\nChat {chat.ref:6} {chat.name or '(a dm)'} — members: {members}"
        )
        for message in sorted(draft.messages, key=lambda m: m.order):
            if message.chat != chat.ref:
                continue
            marks = []
            if message.reply_to:
                marks.append(f"reply to {message.reply_to}")
            if not message.read_by_actor:
                marks.append("UNREAD by you")
            if message.reactors:
                marks.append(f"{message.reaction_emoji} x{len(message.reactors)}")
            suffix = f"  ({'; '.join(marks)})" if marks else ""
            lines.append(
                f"  {message.ref:6} order {message.order:<3} [{message.sender}]: "
                f"{message.text}{suffix}"
            )
    return "\n".join(lines)
