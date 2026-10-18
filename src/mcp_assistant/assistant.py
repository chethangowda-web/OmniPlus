"""Core MCP Assistant powered by LangChain + Google Gemini.

This module provides the ``MCPAssistant`` class, which:
1. Initialises a Gemini LLM via ``ChatGoogleGenerativeAI``.
2. Connects to all enabled MCP servers using ``MultiServerMCPClient``.
3. Loads MCP tools and binds them to a LangChain ReAct agent.
4. Exposes a simple ``async chat(message)`` interface for callers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from mcp_assistant.config import Settings
from mcp_assistant.servers.config_builder import build_mcp_config

_SYSTEM_PROMPT = """\
You are an intelligent MCP-powered AI assistant with access to a rich set of tools:

- **Filesystem tools**: Read files, list directories, search for files and content on the local machine.
- **Web search tools**: Search the internet for up-to-date information using DuckDuckGo or Brave Search.
- **GitHub tools** (if enabled): Browse repositories, view issues, pull requests, commits, and source code on GitHub.

Guidelines:
- Always use the most appropriate tool for the task.
- When reading files or exploring repositories, prefer targeted searches over broad directory listings.
- Cite sources (file paths, URLs, repository links) in your answers where relevant.
- If a tool call fails, explain why and suggest an alternative approach.
- Be concise but thorough. Use markdown formatting to present structured information clearly.
- Never invent file contents or search results — always use the actual tool output.
"""


class MCPAssistant:
    """LangChain ReAct agent backed by Google Gemini and MCP tools.

    Usage::

        assistant = MCPAssistant(settings)
        await assistant.setup()
        response = await assistant.chat("List Python files in ~/projects")
        print(response)

    Args:
        settings: Application settings containing API keys and configuration.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.2,
        )
        self._tools: list[Any] = []
        self._agent: Any = None
        self._mcp_client: MultiServerMCPClient | None = None
        self._history: list = []  # conversation history

    async def setup(self) -> None:
        """Initialise the MCP client, load tools, and create the ReAct agent.

        This must be called before ``chat()`` or ``get_tool_names()``.
        In langchain-mcp-adapters >= 0.1.0 MultiServerMCPClient is NOT a
        context manager — just call get_tools() directly.
        """
        mcp_config = build_mcp_config(self._settings)
        self._mcp_client = MultiServerMCPClient(mcp_config)
        self._tools = await self._mcp_client.get_tools()

        self._agent = create_react_agent(
            model=self._llm,
            tools=self._tools,
            prompt=_SYSTEM_PROMPT,
        )

    async def chat(self, message: str) -> str:
        """Run the agent with a user message and return the response text.

        Args:
            message: The user's natural-language query.

        Returns:
            The assistant's response as a plain string (may contain markdown).

        Raises:
            RuntimeError: If ``setup()`` has not been called yet.
        """
        if self._agent is None:
            raise RuntimeError("MCPAssistant.setup() must be called before chat().")

        self._history.append(("human", message))
        result = await self._agent.ainvoke({"messages": self._history})

        # The agent returns a dict with a "messages" list; the last message is
        # the AIMessage containing the final answer.
        messages = result.get("messages", [])
        if messages:
            last = messages[-1]
            # Support both AIMessage objects and plain dicts.
            if hasattr(last, "content"):
                content = str(last.content)
            elif isinstance(last, dict):
                content = str(last.get("content", ""))
            else:
                content = "(No response)"
            self._history.append(("assistant", content))
            return content
        return "(No response)"

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self._history = []

    def save_history(self) -> None:
        """Save conversation history to ~/.mcp-assistant/history.json."""
        history_dir = Path.home() / ".mcp-assistant"
        history_dir.mkdir(exist_ok=True)
        history_file = history_dir / "history.json"
        serializable = [
            {"role": role, "content": content}
            for role, content in self._history
        ]
        with open(history_file, "w") as f:
            json.dump(serializable, f, indent=2)

    def get_tool_names(self) -> list[str]:
        """Return the names of all currently loaded MCP tools.

        Returns:
            Sorted list of tool name strings.
        """
        return [t.name for t in self._tools]

    async def close(self) -> None:
        """Clean up MCP client connections.

        Note: In langchain-mcp-adapters >= 0.1.0 the client does not maintain
        persistent connections, so no explicit cleanup is needed.
        """
        # MultiServerMCPClient in v0.1.0+ does not support __aexit__.
        # Each tool call opens and closes its own session, so nothing to close.
        pass
