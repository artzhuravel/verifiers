"""What `seed.build` refuses, and what it quietly allows.

The line between the two is the whole point of the module: a draft that would produce a world the
prompt no longer describes is rejected, and the one thing it does silently override is a rule the
authoring model was never told about.
"""

import pytest

from my_env2.seed import (
    ACTOR_HANDLE,
    ME,
    DraftChat,
    DraftError,
    DraftMessage,
    DraftUser,
    WorldDraft,
    build,
)


def draft(**overrides) -> WorldDraft:
    """A two-person, one-chat world with two threaded messages."""
    base = {
        "actor_name": "You",
        "users": [
            DraftUser(ref="u1", name="Ana", handle="ana"),
            DraftUser(ref="u2", name="Bo", handle="bo"),
        ],
        "chats": [DraftChat(ref="c1", name="launch", members=["u1", "u2"])],
        "messages": [
            DraftMessage(
                ref="m1",
                chat="c1",
                sender="u1",
                text="the backfill job times out",
                order=1,
            ),
            DraftMessage(
                ref="m2",
                chat="c1",
                sender="u2",
                text="stale counters are survivable",
                order=2,
                reply_to="m1",
                reactors=["u1"],
            ),
        ],
    }
    return WorldDraft(**{**base, **overrides})


def test_the_ordinary_case_builds():
    state, binding = build(draft())
    assert binding == {}
    assert list(state.chats) == ["c_001"]
    assert [m.id for m in state.messages] == ["m_001", "m_002"]
    assert state.messages[1].reply_to == "m_001"
    assert state.messages[1].reactions == {":+1:": ["u_ana"]}
    assert state.chats["c_001"].member_ids == [ME, "u_ana", "u_bo"]


def test_the_clock_is_order_not_list_position():
    """Filler has to be able to interleave with the core history, not pile up after it."""
    late, early = draft().messages
    late.order, early.order = 1, 2
    state, _ = build(draft(messages=[early, late]))
    assert [m.text for m in state.messages] == [
        "the backfill job times out",
        "stale counters are survivable",
    ]
    assert [m.ts for m in state.messages] == [1, 2]


@pytest.mark.parametrize(
    "change,complaint",
    [
        ({"handle": "you"}, "your own handle"),
        ({"handle": "ana"}, "already taken"),
    ],
)
def test_a_colliding_handle_is_refused_not_renamed(change, complaint):
    """Handles are the one thing this environment promises never collide. Renaming the duplicate
    would honour the letter of that and build a world nobody asked for."""
    extra = DraftUser(ref="u3", name="Someone", handle=change["handle"])
    with pytest.raises(DraftError, match=complaint):
        build(draft(users=[*draft().users, extra]))


def test_a_sender_outside_the_chat_is_refused():
    stray = DraftMessage(ref="m3", chat="c1", sender="u3", text="hello there", order=3)
    with pytest.raises(DraftError, match="undeclared sender"):
        build(draft(messages=[*draft().messages, stray]))


def test_a_reply_across_chats_is_refused():
    other = DraftChat(ref="c2", name="other", members=["u1"])
    crossing = DraftMessage(
        ref="m3",
        chat="c2",
        sender="u1",
        text="a reply elsewhere",
        order=3,
        reply_to="m1",
    )
    with pytest.raises(DraftError, match="across chats"):
        build(
            draft(chats=[*draft().chats, other], messages=[*draft().messages, crossing])
        )


def test_a_reply_before_its_parent_on_the_clock_is_refused():
    parent, child = draft().messages
    child.order = 0  # earlier than its parent
    with pytest.raises(DraftError, match="not an earlier message"):
        build(draft(messages=[parent, child]))


def test_a_reactor_who_is_not_in_the_chat_is_refused():
    """Reactions decide `message_most_reacted`, which needs a strict maximum, so a quietly
    dropped reactor can turn an intended clear winner into a tie."""
    other = DraftChat(ref="c2", name="other", members=["u1"])
    outsider = DraftMessage(
        ref="m3",
        chat="c2",
        sender="u1",
        text="nobody else here",
        order=3,
        reactors=["u2"],
    )
    with pytest.raises(DraftError, match="not in"):
        build(
            draft(chats=[*draft().chats, other], messages=[*draft().messages, outsider])
        )


def test_the_actor_is_the_one_reactor_removed_rather_than_refused():
    """The no-seeded-reactions rule exists so a task's own `add_reaction` is not a no-op — and it
    is a rule the draft was never told about, so it is applied rather than complained about."""
    parent, child = draft().messages
    child.reactors = ["actor", "u1"]
    state, _ = build(draft(messages=[parent, child]))
    assert state.messages[1].reactions == {":+1:": ["u_ana"]}


def test_a_null_from_the_model_leaves_the_default_standing():
    """A model following the schema conscientiously writes every optional key as null."""
    message = DraftMessage.model_validate(
        {
            "ref": "m1",
            "chat": "c1",
            "sender": "u1",
            "text": "hello",
            "order": 2,
            "reaction_emoji": None,
            "reactors": None,
            "reply_to": None,
            "symbol": None,
        }
    )
    assert (message.reaction_emoji, message.reactors, message.reply_to) == (
        ":+1:",
        [],
        None,
    )


def test_an_unbound_placeholder_is_refused():
    with pytest.raises(DraftError, match="which nothing instantiates"):
        build(draft(), {"$chat_0": "chat"})


def test_a_placeholder_bound_to_the_wrong_type_is_refused():
    users = draft().users
    users[0].symbol = "$chat_0"
    with pytest.raises(DraftError, match="must be a chat"):
        build(draft(users=users), {"$chat_0": "chat"})


def test_a_placeholder_claimed_twice_is_refused():
    users = draft().users
    users[0].symbol = users[1].symbol = "$user_0"
    with pytest.raises(DraftError, match="claimed by two entities"):
        build(draft(users=users), {"$user_0": "user"})


def test_a_placeholder_the_sequence_never_asked_for_is_refused():
    users = draft().users
    users[0].symbol = "$user_9"
    with pytest.raises(DraftError, match="never asked for"):
        build(draft(users=users), {})


def test_the_actor_joins_every_chat_without_being_listed():
    """`list_chats` shows only the actor's chats, so a chat the actor is not in is invisible —
    and an invisible entity cannot be referred to, resolved, or acted on."""
    state, _ = build(
        draft(chats=[DraftChat(ref="c1", name="solo", members=[])], messages=[])
    )
    assert state.chats["c_001"].member_ids == [ME]


def test_the_actors_handle_is_reserved_and_not_authored():
    """The model kept picking a handle for itself and then giving a colleague the same one, because
    it reads `users` as "everyone, including me". Reserving one removes the collision."""
    state, _ = build(draft())
    assert state.users[ME].handle == ACTOR_HANDLE
    with pytest.raises(DraftError, match="your own handle"):
        build(
            draft(
                users=[DraftUser(ref="u1", name="Ana", handle=ACTOR_HANDLE)],
                chats=[DraftChat(ref="c1", name="launch", members=["u1"])],
                messages=[],
            )
        )


def test_an_at_prefix_on_a_handle_is_stripped():
    state, _ = build(
        draft(
            users=[DraftUser(ref="u1", name="Ana", handle="@ana")],
            chats=[DraftChat(ref="c1", name="launch", members=["u1"])],
            messages=[],
        )
    )
    assert [user.handle for user in state.users.values()] == [ACTOR_HANDLE, "ana"]
