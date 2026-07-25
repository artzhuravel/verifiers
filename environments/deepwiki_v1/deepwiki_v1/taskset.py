"""Remote-tool example backed by the public DeepWiki MCP server.

Unlike the locally authored `glossary` and worker-shared `wiki_search` examples,
`DeepWikiToolset` declares no local `@tool` methods. Its config supplies an existing
streamable-HTTP URL, so verifiers connects the harness directly to that remote server.
The harness runtime therefore needs outbound network access.
"""

import os

import verifiers.v1 as vf

from deepwiki_v1.servers.deepwiki import DEEPWIKI_URL, DeepWikiToolset

# (repository, expected primary language) pairs chosen for unambiguous answers.
TASKS = [
    ("modelcontextprotocol/python-sdk", "python"),
    ("tokio-rs/tokio", "rust"),
    ("karpathy/nanochat", "python"),
    ("microsoft/playwright", "typescript"),
]


class DeepWikiTaskConfig(vf.TaskConfig):
    tools: vf.ToolsetConfig = vf.ToolsetConfig(url=DEEPWIKI_URL)
    judges: vf.Judges = [
        vf.ReferenceJudgeConfig(
            model="openai/gpt-5-nano",
            base_url=os.environ["OPENROUTER_BASE_URL"],
            api_key_var="OPENROUTER_API_KEY",
            answer_field="answer",
            question_field="question",
        )
    ]


class DeepWikiTaskData(vf.TaskData):
    question: str
    """The plain question the reference judge reads as `{question}`."""
    answer: str
    """The reference answer the judge grades the model's reply against."""


class DeepWikiTask(vf.Task[DeepWikiTaskData, vf.State, DeepWikiTaskConfig]):
    tools = (DeepWikiToolset,)

    # @vf.reward(weight=1.0)
    # async def answered(self, trace: vf.Trace) -> float:
    #     last = trace.last_reply
    #     return float(self.data.answer.lower() in (last or "").lower())


class DeepWikiConfig(vf.TasksetConfig):
    task: DeepWikiTaskConfig = DeepWikiTaskConfig()


class DeepWikiTaskset(vf.Taskset[DeepWikiTask, DeepWikiConfig]):
    def load(self) -> list[DeepWikiTask]:
        return [
            DeepWikiTask(
                DeepWikiTaskData(
                    idx=i,
                    name=repo,
                    # The judge reads this clean question as `{question}`.
                    question=(
                        f'What programming language is the "{repo}" GitHub '
                        "repository primarily written in?"
                    ),
                    # The model sees this framed instruction (tool use + answer format).
                    prompt=(
                        f"Use the `deepwiki_ask_question` tool to find what programming "
                        f'language the "{repo}" GitHub repository is primarily written in. '
                        "Then reply with just the language name."
                    ),
                    answer=language,
                ),
                self.config.task,
            )
            for i, (repo, language) in enumerate(TASKS)
        ]
