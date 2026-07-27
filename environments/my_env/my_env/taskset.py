"""my-env: a mock chat app for automatically generated tool-use tasks.

`ChatTaskset.load()` either live-generates task scaffolds (see generate.py and
../DESIGN.md) or, when `dataset` is set, loads LLM-authored tasks from a JSONL (see
author.py). Each `GeneratedTask` is scored by three rewards: the state-diff (chat
effects), tool-call well-formedness, and an LLM judge over open-ended DeepWiki answers.

Hand-written example tasks live in `legacy_tasksets.py` (not loaded here).
"""

import json
from pathlib import Path

import verifiers.v1 as vf

from my_env.adapter import ChatAdapter
from my_env.generate import generate
from my_env.servers.tool import ChatToolset
from my_env.servers.web import DEEPWIKI_URL, DeepWikiToolset, WebToolsetConfig
from my_env.state import ChatState
from my_env.verify import judge_open_ended, score, tool_call_score

_ACTION_SPEC = json.loads((Path(__file__).parent / "action_spec.json").read_text())
_ADAPTER = ChatAdapter()  # stateless; reused for verification


class ChatTaskConfig(vf.TaskConfig):
    tools: vf.ToolsetConfig = vf.ToolsetConfig()
    web: WebToolsetConfig = WebToolsetConfig(url=DEEPWIKI_URL)
    """DeepWiki remote toolset config — the distinct type lets the resolver pair it to
    `DeepWikiToolset` while `tools` pairs to `ChatToolset`."""
    judge: vf.JudgeConfig = vf.JudgeConfig(
        model="openai/gpt-5-mini",
        base_url="https://openrouter.ai/api/v1",
        api_key_var="OPENROUTER_API_KEY",
    )
    """LLM judge for open-ended answers — its own endpoint (doesn't inherit the eval client)."""


class ChatTaskData(vf.TaskData):
    pass


def _seed_trace(trace: vf.Trace, source: ChatState) -> None:
    # Copy a conversation into the rollout's isolated state. Called from Task.setup,
    # before the state channel is served, so the tools see the seed.
    seed = source.model_copy(deep=True)
    trace.state.me = seed.me
    trace.state.users = seed.users
    trace.state.chats = seed.chats
    trace.state.messages = seed.messages
    trace.state.next_message_id = seed.next_message_id
    trace.state.next_chat_id = seed.next_chat_id


class ChatTask(vf.Task[ChatTaskData, ChatState, ChatTaskConfig]):
    """Base for generated chat tasks: the tools; subclasses seed state and score."""

    tools = (ChatToolset,)


class GeneratedTaskData(ChatTaskData):
    seed: ChatState
    """The initial conversation this task is seeded with (per-task varied)."""
    expected: ChatState
    """The state after a faithful run of the plan — the reward's comparison target."""
    steps: list[dict]
    """Flat ordered steps [{action, tool, kind, objects, args, expect_error,
    entity_id}] the agent is asked to perform (kept for reference/prompt-building)."""
    open_ended: list[dict] = []
    """[{question, ground_truth, judge_hint}] for the DeepWiki judge; [] when unauthored."""


def _instruction(step: dict) -> str:
    tool, a = step["tool"], step["args"]
    if step.get("open_ended"):
        # Placeholder — the LLM authoring step fills the repo/question and expected answer.
        return f"Make an open-ended query with `{tool}` (specifics up to the task author)  [{tool}]"
    if tool == "chat_list_chats":
        text = "List your chats"
    elif tool == "chat_read_messages":
        text = f"Read messages in chat {a['chat_id']}"
    elif tool == "chat_get_user":
        text = f"Look up user {a['user_id']}"
    elif tool == "chat_send_message":
        text = f'Send the message "{a["text"]}" to chat {a["chat_id"]}'
    elif tool == "chat_reply_to":
        text = f'Reply "{a["text"]}" to message {a["message_id"]}'
    elif tool == "chat_add_reaction":
        text = f'React "{a["emoji"]}" to message {a["message_id"]}'
    elif tool == "chat_mark_read":
        text = f"Mark chat {a['chat_id']} as read"
    else:  # chat_create_chat
        named = f"named {a['name']!r} " if a.get("name") else ""
        text = f"Create a chat {named}with members {a['member_ids']}"
    return f"{text}  [{tool}]"


def _render_prompt(timeline: list[list[dict]]) -> str:
    lines = [
        "You are user u_me in a chat app. Perform the following actions in order using "
        "the chat tools. Some may fail because they reference something that does not "
        "exist — attempt each as written and continue. Reply 'done' when finished.",
        "",
    ]
    for t, group in enumerate(timeline, 1):
        lines.append(f"Timestep {t}:")
        lines.extend(f"  - {_instruction(step)}" for step in group)
    return "\n".join(lines)


def _transcript(trace: vf.Trace) -> str:
    # The agent's answer-bearing output for the judge: messages it sent + its final reply.
    state = trace.state
    sent = []
    for message in state.messages:
        if message.sender_id == state.me:
            chat = state.chats.get(message.chat_id)
            label = chat.name if chat and chat.name else message.chat_id
            sent.append(f"[{label}] {message.text}")
    body = "\n".join(sent) or "(none)"
    return f"Messages the agent sent:\n{body}\n\nAgent's final reply:\n{trace.last_reply or ''}"


class GeneratedTask(ChatTask):
    # Both toolsets: local chat (stateful) + remote DeepWiki (open-ended slots).
    tools = (ChatToolset, DeepWikiToolset)

    async def setup(self, trace: vf.Trace) -> None:
        _seed_trace(trace, self.data.seed)

    @vf.reward(weight=0.5)
    async def state_diff(self, trace: vf.Trace) -> float:
        return score(self.data.seed, self.data.expected, trace, _ADAPTER)

    @vf.reward(weight=0.2)
    async def tool_calls(self, trace: vf.Trace) -> float:
        return tool_call_score(trace, _ACTION_SPEC)

    @vf.reward(weight=0.3)
    async def open_ended(self, trace: vf.Trace) -> float:
        return await judge_open_ended(
            self.data.open_ended, _transcript(trace), self.config.judge, trace=trace
        )


class ChatConfig(vf.TasksetConfig):
    task: ChatTaskConfig = ChatTaskConfig()
    dataset: str | None = None
    """Path to an LLM-authored tasks JSONL (author.py). Set = load it; unset = live-generate."""
    num_generated: int = 5
    """How many tasks to generate (live mode)."""
    timesteps: int = 3
    max_actions_per_t: int = 3
    p_invalid: float = 0.2
    p_open: float = 0.15
    """Probability a drawn action is an open-ended (e.g. DeepWiki) slot for the LLM to fill."""


class ChatTaskset(vf.Taskset[ChatTask, ChatConfig]):
    def load(self) -> list[ChatTask]:
        config = self.config
        if config.dataset:
            # LLM-authored tasks (frozen JSONL): authored prompt + open-ended golds.
            rows = [
                json.loads(line)
                for line in Path(config.dataset).read_text().splitlines()
                if line.strip()
            ]
            return [
                GeneratedTask(
                    GeneratedTaskData(
                        idx=row["idx"],
                        prompt=row["prompt"],
                        seed=ChatState.model_validate(row["seed"]),
                        expected=ChatState.model_validate(row["expected"]),
                        steps=row["steps"],
                        open_ended=row.get("open_ended", []),
                    ),
                    config.task,
                )
                for row in rows
            ]
        adapter = ChatAdapter()
        # All actions in the spec: chat (stateful) + deepwiki (open-ended). The generator
        # classifies them; open-ended ones become slots and never touch the adapter.
        action_ids = [a["id"] for a in _ACTION_SPEC["actions"]]
        tasks: list[ChatTask] = []
        for idx in range(config.num_generated):
            seed, expected, timeline = generate(
                _ACTION_SPEC, adapter, action_ids,
                config.timesteps, config.max_actions_per_t, config.p_invalid, config.p_open, idx,
            )
            steps = [step for group in timeline for step in group]
            tasks.append(
                GeneratedTask(
                    GeneratedTaskData(
                        idx=idx, prompt=_render_prompt(timeline),
                        seed=seed, expected=expected, steps=steps,
                    ),
                    config.task,
                )
            )
        return tasks
