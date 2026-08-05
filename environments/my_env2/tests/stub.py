"""A world author with no model behind it.

Stages 3 and 5 are the only places the pipeline needs invention, and invention is exactly what
cannot be tested cheaply. This builds a mechanical world that satisfies any manifest — dull, but
structurally valid — so the deterministic spine underneath the authoring stages (binding,
reference resolution, replay, expected state) can be exercised over a hundred sequences without
a single API call.
"""

from my_env2.llm import AuthoringError
from my_env2.seed import DraftChat, DraftMessage, DraftUser, WorldDraft
from my_env2.symbolic import Sequence


def stub_world(
    sequence: Sequence, *, extra_users: int = 3, extra_messages: int = 4
) -> WorldDraft:
    """A draft binding every seed symbol, plus a little padding.

    Every message is left unread by the actor, so a `mark_read` always has something to do, and
    a few carry reactions so the superlative modes have a strict maximum to find.
    """
    seed_entries = [entry for entry in sequence.manifest if entry.origin == "seed"]
    wanted = {
        kind: [e.symbol for e in seed_entries if e.entity_type == kind]
        for kind in ("user", "chat", "message")
    }

    users = [
        DraftUser(ref=f"u{i}", name=f"Person {i}", handle=f"person{i}", symbol=symbol)
        for i, symbol in enumerate(wanted["user"])
    ]
    users += [
        DraftUser(ref=f"x{i}", name=f"Extra {i}", handle=f"extra{i}")
        for i in range(extra_users)
    ]
    if not users:
        raise AuthoringError("a world needs at least one other person")

    chats = [
        DraftChat(
            ref=f"c{i}",
            name=f"room-{i}",
            members=[user.ref for user in users[: 2 + i % 2]],
            symbol=symbol,
        )
        for i, symbol in enumerate(wanted["chat"])
    ]
    if not chats:
        chats = [DraftChat(ref="c0", name="room-0", members=[users[0].ref])]

    messages = []
    for i, symbol in enumerate(wanted["message"]):
        chat = chats[i % len(chats)]
        messages.append(
            DraftMessage(
                ref=f"m{i}",
                chat=chat.ref,
                sender=chat.members[i % len(chat.members)],
                text=f"note {i} concerns widget {i} and nothing else",
                order=i + 1,
                read_by_actor=False,
                reactors=chat.members[: i % 3],
                symbol=symbol,
            )
        )
    for i in range(extra_messages):
        chat = chats[i % len(chats)]
        messages.append(
            DraftMessage(
                ref=f"p{i}",
                chat=chat.ref,
                sender=chat.members[i % len(chat.members)],
                text=f"padding {i} mentions gadget {i} in passing",
                order=len(wanted["message"]) + i + 1,
                read_by_actor=False,
            )
        )
    return WorldDraft(
        topic="widgets",
        actor_name="You",
        users=users,
        chats=chats,
        messages=messages,
    )
