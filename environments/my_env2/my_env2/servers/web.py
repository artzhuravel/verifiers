"""Remote DeepWiki tool server: read-only GitHub-repo Q&A over MCP.

No local `@tool` methods — the config carries a streamable-HTTP URL and verifiers
connects the harness straight to the remote server (same as `deepwiki_v1`). The
rollout runtime therefore needs outbound network access. Exposes
`deepwiki_ask_question`, `deepwiki_read_wiki_contents`, `deepwiki_read_wiki_structure`.

`WebToolsetConfig` is a distinct config subclass so a task carrying both this and
`ChatToolset` (which uses plain `ToolsetConfig`) pairs each toolset to its own
config field by exact type — the resolver rejects two same-typed fields.
"""

import verifiers.v1 as vf

DEEPWIKI_URL = "https://mcp.deepwiki.com/mcp"


class WebToolsetConfig(vf.ToolsetConfig):
    pass


class DeepWikiToolset(vf.Toolset[WebToolsetConfig]):
    TOOL_PREFIX = "deepwiki"


if __name__ == "__main__":
    DeepWikiToolset.run()
