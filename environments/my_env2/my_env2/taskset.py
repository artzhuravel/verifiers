"""The taskset: serving persisted task records to an eval.

Generation and evaluation are deliberately separate. The pipeline is LLM-costed and
nondeterministic, so its output is a frozen artifact; this file only reads it. There is no
live-generate mode, because a task whose world was invented during the eval could not have had
its references checked for uniqueness first, which is the one thing the whole design rests on.

Every row carries three prompts over one `(seed, expected)` pair, and `level` picks which one is
served. The triple is matched by construction: nothing but the specification's explicitness
differs, so a score gap between two levels measures the gap and not authoring noise.
"""

import json
from pathlib import Path

import verifiers.v1 as vf

from my_env2.adapter import ChatAdapter
from my_env2.servers.tool import ChatToolset
from my_env2.servers.web import DEEPWIKI_URL, DeepWikiToolset, WebToolsetConfig
from my_env2.state import ChatState
from my_env2.verify import judge_score, transcript
from my_env2.verify import state_diff as compare_states

_ADAPTER = ChatAdapter()  # stateless; reused for verification


def _judge_for(row: dict, level: str) -> list[dict]:
    """This level's judge items.

    A task file written before the items were restated per level carries one flat list, authored
    against level 1. Serving it at a higher level is not wrong — the requirement is the same — but
    its `hint` will name steps and ids the prompt no longer contains, so it is used and the
    mismatch is left visible rather than silently corrected.
    """
    judge = row.get("judge") or []
    if isinstance(judge, dict):
        return judge.get(level) or judge.get("1") or []
    return judge


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
    """The delivery judge — its own endpoint, so it does not inherit the eval client."""


class AuthoredTaskData(vf.TaskData):
    seed: ChatState
    """The workspace this task starts from, authored to make its sequence make sense."""
    expected: ChatState
    """The workspace after a faithful run — the deterministic reward's comparison target."""
    judge: list[dict] = []
    """[{id, requirement, expected, hint}] — information that had to reach a message or the
    final reply, which no state comparison can see. Already narrowed to the served level: the
    items are restated at every rung, so the wrong level's items name steps and ids that this
    level's prompt does not contain."""


class AuthoredTask(vf.Task[AuthoredTaskData, ChatState, ChatTaskConfig]):
    # Both toolsets: the local chat app, and DeepWiki for the steps that ask something outside
    # the workspace.
    tools = (ChatToolset, DeepWikiToolset)

    async def setup(self, trace: vf.Trace) -> None:
        # Copy the seed into the rollout's isolated state, before the state channel is served,
        # so the tools see the workspace the prompt describes.
        seed = self.data.seed.model_copy(deep=True)
        trace.state.me = seed.me
        trace.state.users = seed.users
        trace.state.chats = seed.chats
        trace.state.messages = seed.messages
        trace.state.next_message_id = seed.next_message_id
        trace.state.next_chat_id = seed.next_chat_id

    @vf.reward(weight=0.6)
    async def state_diff(self, trace: vf.Trace) -> float:
        return compare_states(self.data.seed, self.data.expected, trace, _ADAPTER)

    @vf.reward(weight=0.4)
    async def delivery(self, trace: vf.Trace) -> float:
        seeded = {message.id for message in self.data.seed.messages}
        return await judge_score(
            self.data.judge, transcript(trace, seeded), self.config.judge, trace=trace
        )


class ChatConfig(vf.TasksetConfig):
    task: ChatTaskConfig = ChatTaskConfig()
    dataset: str = "tmp/tasks_v2.jsonl"
    """Rows written by `python -m my_env2.pipeline`."""
    level: int = 3
    """Which prompt to serve: 1 explicit and numbered, 2 prose with described references,
    3 goal-level, 4 folded — the message a colleague would have typed. Same seed and same expected
    state at every level; the judge items say the same thing but are restated per level, since the
    higher rungs remove the steps and ids the lower ones lean on."""
    limit: int | None = None


class ChatTaskset(vf.Taskset[AuthoredTask, ChatConfig]):
    def load(self) -> list[AuthoredTask]:
        config = self.config
        if config.level not in (1, 2, 3, 4):
            raise ValueError(f"level must be 1, 2, 3 or 4, got {config.level}")
        path = Path(config.dataset)
        if not path.exists():
            raise FileNotFoundError(
                f"no task file at {path} — run `python -m my_env2.pipeline --out {path}` first"
            )
        rows = [
            json.loads(line) for line in path.read_text().splitlines() if line.strip()
        ]
        level = str(config.level)
        missing = [row["idx"] for row in rows[: config.limit] if level not in row["prompts"]]
        if missing:
            raise ValueError(
                f"{path} has no level-{level} prompt for task(s) {missing} — it was written before "
                f"level {level} existed. Re-run `python -m my_env2.pipeline` to author it."
            )
        return [
            AuthoredTask(
                AuthoredTaskData(
                    idx=row["idx"],
                    prompt=row["prompts"][level],
                    seed=ChatState.model_validate(row["seed"]),
                    expected=ChatState.model_validate(row["expected"]),
                    judge=_judge_for(row, level),
                ),
                config.task,
            )
            for row in rows[: config.limit]
        ]
