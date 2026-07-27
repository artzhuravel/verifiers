"""Hand-written example chat tasks — superseded by the generator, kept for reference.

Not loaded by `ChatTaskset`. They demonstrate three reward patterns against the fixed
`state.SAMPLE` conversation: known-answer retrieval (`ReadTask`), goal-state writes
(`WriteProbeTask`), and a composed DeepWiki web-read -> chat-write (`WebToChatTask`).
To run them, load them from a taskset of your own.
"""

import verifiers.v1 as vf

from my_env.servers.tool import ChatToolset
from my_env.servers.web import DeepWikiToolset
from my_env.state import SAMPLE, ChatState
from my_env.taskset import ChatTaskConfig, ChatTaskData, _seed_trace

READ_SYSTEM = (
    "You are using a chat app. Use the `chat_list_chats`, `chat_read_messages`, and "
    "`chat_get_user` tools to inspect it, then answer the question concisely."
)

# (question, known answer) pairs about the seeded conversation in state.SAMPLE.
READ_TASKS = [
    ("Who sent the last message in the 'launch' chat? Reply with just their name.", "Alice"),
    ("How many messages are in the 'launch' chat? Reply with just the number.", "3"),
]

# Explicit, id-anchored instructions so the probe tests the write tools, not discovery.
WRITE_PROMPT = (
    "You are user u_me in a chat app. Do all three actions using the chat tools:\n"
    "1. Send the message 'running 5 min late' to the chat with id c_launch "
    "(`chat_send_message`).\n"
    "2. Add a ':+1:' reaction to the message with id m_001 (`chat_add_reaction`).\n"
    "3. Create a new group chat named 'coffee' that includes user u_bob "
    "(`chat_create_chat`).\n"
    "After all three are done, reply with just 'done'."
)

# Composed web -> chat tasks: ask DeepWiki a stable-answer question, post the answer
# to the chat. (repo, known primary language) — languages kept collision-safe.
WEB_TASKS = [
    ("modelcontextprotocol/python-sdk", "python"),
    ("tokio-rs/tokio", "rust"),
    ("microsoft/playwright", "typescript"),
]

WEB_PROMPT = (
    "Use the `deepwiki_ask_question` tool to find what programming language the "
    'GitHub repository "{repo}" is primarily written in. Then send a message '
    "containing just that language name to the chat with id c_launch using "
    "`chat_send_message`. Reply 'done' when finished."
)


class LegacyTaskData(ChatTaskData):
    answer: str = ""
    """The known answer for read tasks; unused by the write probe."""


class LegacyChatTask(vf.Task[LegacyTaskData, ChatState, ChatTaskConfig]):
    """Base for the demo tasks: shared tools + seeding from the fixed SAMPLE.

    Uses `ChatTaskConfig`, which now carries the `web` field DeepWiki needs."""

    tools = (ChatToolset,)

    async def setup(self, trace: vf.Trace) -> None:
        _seed_trace(trace, SAMPLE)


class ReadTask(LegacyChatTask):
    @vf.reward(weight=1.0)
    async def correct(self, trace: vf.Trace) -> float:
        # Lenient substring match — fine for these short factual answers.
        reply = (trace.last_reply or "").strip().lower()
        return float(self.data.answer.strip().lower() in reply)


class WriteProbeTask(LegacyChatTask):
    @vf.reward(weight=1.0)
    async def did_actions(self, trace: vf.Trace) -> float:
        # Goal-state check: read the final per-rollout state and score the fraction
        # of the three requested mutations that actually landed.
        state = trace.state
        sent = any(
            m.sender_id == state.me and "running 5 min late" in m.text.lower()
            for m in state.messages
        )
        m_001 = next((m for m in state.messages if m.id == "m_001"), None)
        reacted = m_001 is not None and any(
            state.me in reactors for reactors in m_001.reactions.values()
        )
        created = any(chat.name == "coffee" for chat in state.chats.values())
        return (sent + reacted + created) / 3


class WebToChatTask(LegacyChatTask):
    tools = (ChatToolset, DeepWikiToolset)

    @vf.reward(weight=1.0)
    async def posted(self, trace: vf.Trace) -> float:
        # Goal-state: a message from the user in c_launch containing the known language
        # (which the agent had to obtain from DeepWiki first).
        state = trace.state
        return float(
            any(
                m.chat_id == "c_launch"
                and m.sender_id == state.me
                and self.data.answer.lower() in (m.text or "").lower()
                for m in state.messages
            )
        )
