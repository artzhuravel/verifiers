"""The seeded world: a small company's chat workspace.

A fixed, hand-authored cast and message history, built fresh per task by
`build_world(rng)`. The structure is deliberately constant — the same 24 users, 6 chats
and 40 messages every time — so that natural references ("the launch channel", "the
other Alex") mean the same thing across tasks and a human can learn the world once when
checking golds. Only the read state varies with `rng`.

The world is built to make *referential* difficulty possible, which a one-chat seed
cannot express:

- **Colliding names.** Three people are called Alex, two Sam, two Jordan, two Priya, two
  Chris — and the two Chrises are in the *same* chat, disagreeing with each other. A name
  never identifies a user; only the handle or the chat context does.
- **Colliding topics.** The Q3 launch date is argued about in three places (`launch`,
  `launch-eng`, and a DM); the onboarding flow in two (`design-review`, `onboarding`).
  "the chat where we discussed the launch" is genuinely ambiguous; "the chat where Wei
  posted the migration failures" is not.
- **Threads.** Every chat has one `reply_to` chain, so a message can be addressed by its
  position in a conversation rather than by id.

Ids are readable (`u_alex_chen`), as in a real workspace — the ambiguity comes from the
colliding *names*, not from opaque keys.
"""

from random import Random

from my_env.state import Chat, ChatState, Message, User

ME = "u_me"

# (id, display name, handle) — display names collide on purpose; handles never do.
_USERS: list[tuple[str, str, str]] = [
    (ME, "You", "you"),
    ("u_alex_chen", "Alex", "alex.chen"),
    ("u_alex_kim", "Alex", "alex.kim"),
    ("u_alex_rivera", "Alex", "arivera"),
    ("u_sam_okafor", "Sam", "sam.okafor"),
    ("u_sam_patel", "Sam", "spatel"),
    ("u_jordan_lee", "Jordan", "jordan.lee"),
    ("u_jordan_blake", "Jordan", "jblake"),
    ("u_priya_nair", "Priya", "priya.nair"),
    ("u_priya_raman", "Priya", "praman"),
    ("u_chris_moreau", "Chris", "chris.m"),
    ("u_chris_dunn", "Chris", "cdunn"),
    ("u_maya", "Maya", "maya"),
    ("u_tomas", "Tomás", "tomas"),
    ("u_ingrid", "Ingrid", "ingrid"),
    ("u_wei", "Wei", "wei"),
    ("u_fatima", "Fatima", "fatima"),
    ("u_diego", "Diego", "diego"),
    ("u_hana", "Hana", "hana"),
    ("u_noor", "Noor", "noor"),
    ("u_bekele", "Bekele", "bekele"),
    ("u_lena", "Lena", "lena"),
    ("u_yusuf", "Yusuf", "yusuf"),
    ("u_rosa", "Rosa", "rosa"),
]

# (id, kind, name, members) — you are in every chat, so everything is discoverable
# through `list_chats`; membership otherwise varies.
_CHATS: list[tuple[str, str, str | None, list[str]]] = [
    ("c_001", "group", "launch",
     [ME, "u_alex_chen", "u_priya_nair", "u_jordan_lee", "u_maya", "u_fatima"]),
    ("c_002", "group", "launch-eng",
     [ME, "u_alex_kim", "u_sam_okafor", "u_wei", "u_diego", "u_chris_moreau", "u_chris_dunn"]),
    ("c_003", "group", "design-review",
     [ME, "u_priya_raman", "u_hana", "u_tomas", "u_alex_rivera", "u_lena"]),
    ("c_004", "group", "onboarding",
     [ME, "u_sam_patel", "u_noor", "u_bekele", "u_jordan_blake", "u_rosa"]),
    ("c_005", "dm", None, [ME, "u_alex_chen"]),
    ("c_006", "group", "watercooler",
     [ME, "u_maya", "u_diego", "u_rosa", "u_yusuf", "u_ingrid", "u_hana"]),
]

# (id, chat, sender, text, reply_to) — ids are sequential and `ts` is the position in
# this list, so the whole history is one coherent logical clock.
_MESSAGES: list[tuple[str, str, str, str, str | None]] = [
    # launch — GTM side of the Q3 launch. Thread: m_002 -> m_003 -> m_004 -> m_005.
    ("m_001", "c_001", "u_priya_nair", "Reminder: GTM copy freeze is Thursday.", None),
    ("m_002", "c_001", "u_alex_chen", "Are we still holding the Q3 date?", None),
    ("m_003", "c_001", "u_jordan_lee", "Eng says the migration is the long pole.", "m_002"),
    ("m_004", "c_001", "u_priya_nair", "If it slips we have to redo the press embargo.", "m_003"),
    ("m_005", "c_001", "u_maya", "I can move the embargo to the 14th, but not past it.", "m_004"),
    ("m_006", "c_001", "u_fatima", "Launch review deck is in the shared drive.", None),
    ("m_007", "c_001", "u_alex_chen", "Thanks — I'll review it tonight.", None),
    # launch-eng — same launch date, different room, different people.
    # Thread: m_008 -> m_009 -> m_010 -> m_011. Both Chrises speak, and disagree.
    ("m_008", "c_002", "u_alex_kim", "Migration dry run finished: 3 failures.", None),
    ("m_009", "c_002", "u_wei", "Two are flaky. The third is real — the backfill job times out.", "m_008"),
    ("m_010", "c_002", "u_sam_okafor", "Could we ship the Q3 date without the backfill?", "m_009"),
    ("m_011", "c_002", "u_diego", "Only if we accept stale counters for about a week.", "m_010"),
    ("m_012", "c_002", "u_chris_moreau", "I'd rather slip a week than ship stale counters.", None),
    ("m_013", "c_002", "u_chris_dunn", "Disagree — a week of stale counters is survivable.", None),
    ("m_014", "c_002", "u_alex_kim", "Let's settle it in tomorrow's sync.", None),
    # design-review — the onboarding flow, from the design side.
    # Thread: m_015 -> m_016 -> m_017 -> m_018.
    ("m_015", "c_003", "u_priya_raman", "New onboarding flow is up for review.", None),
    ("m_016", "c_003", "u_hana", "Step 3 asks for too much before showing any value.", "m_015"),
    ("m_017", "c_003", "u_tomas", "Agreed. Can we defer the workspace setup?", "m_016"),
    ("m_018", "c_003", "u_priya_raman", "Deferring it breaks the invite path.", "m_017"),
    ("m_019", "c_003", "u_alex_rivera", "I'll mock up both variants by Friday.", None),
    ("m_020", "c_003", "u_lena", "Please include the empty state this time.", None),
    ("m_021", "c_003", "u_hana", "+1 to the empty state.", None),
    # onboarding — the same flow, from the metrics side. m_024 cross-references
    # design-review by name. Thread: m_022 -> m_023 -> m_024 -> m_025.
    ("m_022", "c_004", "u_sam_patel", "Onboarding completion dropped to 41% this week.", None),
    ("m_023", "c_004", "u_noor", "The drop starts at the workspace setup step.", "m_022"),
    ("m_024", "c_004", "u_bekele", "That's the same step design-review is arguing about.", "m_023"),
    ("m_025", "c_004", "u_jordan_blake", "Should we just merge the two conversations?", "m_024"),
    ("m_026", "c_004", "u_rosa", "I pulled the funnel numbers into a sheet.", None),
    ("m_027", "c_004", "u_sam_patel", "Let's not change anything until the review lands.", None),
    ("m_028", "c_004", "u_noor", "Agreed.", None),
    # DM with Alex Chen — a third place the launch date comes up, and the thread that
    # makes the name collision explicit. Thread: m_030 -> m_031 -> m_032 -> m_033.
    ("m_029", "c_005", "u_alex_chen", "Do you have a read on the Q3 date?", None),
    ("m_030", "c_005", ME, "Eng is leaning toward a one-week slip.", None),
    ("m_031", "c_005", "u_alex_chen", "That matches what the other Alex told me.", "m_030"),
    ("m_032", "c_005", ME, "Which one — Kim or Rivera?", "m_031"),
    ("m_033", "c_005", "u_alex_chen", "Kim. Rivera is on the design side.", "m_032"),
    # watercooler — no work content, so it is a clean negative for topic references.
    # Thread: m_034 -> m_035 -> m_036 -> m_037.
    ("m_034", "c_006", "u_maya", "The espresso machine is making a new noise.", None),
    ("m_035", "c_006", "u_diego", "That's the descale alarm. It's been on for a month.", "m_034"),
    ("m_036", "c_006", "u_rosa", "It's been on since March.", "m_035"),
    ("m_037", "c_006", "u_yusuf", "I've started calling it Gerald.", "m_036"),
    ("m_038", "c_006", "u_ingrid", "Gerald deserves better.", None),
    ("m_039", "c_006", "u_hana", "Coffee run at 3?", None),
    ("m_040", "c_006", "u_yusuf", "Always.", None),
]

# (message, emoji, reactors) — never `u_me`, so a seeded reaction can't make a generated
# `add_reaction` on the same message a silent no-op.
_REACTIONS: list[tuple[str, str, list[str]]] = [
    ("m_002", ":eyes:", ["u_jordan_lee", "u_maya"]),
    ("m_005", ":+1:", ["u_alex_chen", "u_priya_nair"]),
    ("m_009", ":eyes:", ["u_alex_kim"]),
    ("m_013", ":eyes:", ["u_wei", "u_diego"]),
    ("m_017", ":+1:", ["u_lena", "u_hana"]),
    ("m_024", ":eyes:", ["u_jordan_blake"]),
    ("m_026", ":+1:", ["u_sam_patel", "u_noor"]),
    ("m_037", ":tada:", ["u_ingrid", "u_rosa", "u_hana", "u_diego"]),
    ("m_038", ":heart:", ["u_yusuf"]),
]

# Chats you are likely to still have unread — kept low so `mark_read` usually has
# something to do (on a fully-read chat it is a silent no-op and rewards nothing).
_CAUGHT_UP_P = 0.3


def _next_id(ids: list[str]) -> int:
    """One past the highest numeric suffix, so minted ids never collide with seeded
    ones. Derived rather than counted — ids are a creation-order counter, not a size."""
    return max((int(i.split("_")[1]) for i in ids), default=0) + 1


def build_world(rng: Random) -> ChatState:
    """The seeded world. Structure is fixed; `rng` only decides which chats you have
    already caught up on. Every container is freshly built, so the two states the
    generator creates (the simulated one and the pristine seed) never share mutables."""
    users = {uid: User(id=uid, name=name, handle=handle) for uid, name, handle in _USERS}
    chats = {
        cid: Chat(id=cid, kind=kind, name=name, member_ids=list(members))
        for cid, kind, name, members in _CHATS
    }
    reactions: dict[str, dict[str, list[str]]] = {}
    for message_id, emoji, reactors in _REACTIONS:
        reactions.setdefault(message_id, {})[emoji] = list(reactors)

    # One draw per chat, in a fixed order: a deterministic number of draws, so the
    # generator's subsequent sampling stays aligned across the two build calls.
    caught_up = {cid for cid, *_ in _CHATS if rng.random() < _CAUGHT_UP_P}

    messages = []
    for ts, (message_id, chat_id, sender, text, reply_to) in enumerate(_MESSAGES, start=1):
        read_by = [sender]
        if ME not in read_by and chat_id in caught_up:
            read_by.append(ME)
        messages.append(
            Message(
                id=message_id, chat_id=chat_id, sender_id=sender, text=text, ts=ts,
                reply_to=reply_to,
                reactions={e: list(u) for e, u in reactions.get(message_id, {}).items()},
                read_by=read_by,
            )
        )

    return ChatState(
        me=ME, users=users, chats=chats, messages=messages,
        next_message_id=_next_id([m.id for m in messages]),
        next_chat_id=_next_id(list(chats)),
    )
