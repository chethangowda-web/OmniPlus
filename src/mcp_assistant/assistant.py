"""Core MCP Assistant powered by LangChain + Google Gemini.

This module provides the ``MCPAssistant`` class, which:
1. Initialises a Gemini LLM via ``ChatGoogleGenerativeAI``.
2. Connects to all enabled MCP servers using ``MultiServerMCPClient``.
3. Loads MCP tools and binds them to a LangChain ReAct agent.
4. Exposes a simple ``async chat(message)`` interface for callers.
"""
from __future__ import annotations

import asyncio
import json
import re
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

_FALLBACK_MODELS = [
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
    "gemma-4-31b-it",
]


class MCPAssistant:
    """LangChain ReAct agent backed by Google Gemini and MCP tools.

    Features intelligent automated model failover across Google AI Studio models
    to seamlessly handle free-tier rate limits and daily quotas.

    Args:
        settings: Application settings containing API keys and configuration.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # Build priority model list with user's configured model first
        user_model = settings.gemini_model
        self._model_pool = [user_model] + [m for m in _FALLBACK_MODELS if m != user_model]
        self._current_model_idx = 0
        self._current_model = self._model_pool[0]

        self._tools: list[Any] = []
        self._agent: Any = None
        self._mcp_client: MultiServerMCPClient | None = None
        self._history: list = []

    def _rebuild_agent_with_model(self, model_name: str) -> None:
        """Switch agent LLM to a fallback model while keeping tools & history intact."""
        self._current_model = model_name
        self._llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self._settings.gemini_api_key,
            temperature=0.2,
            max_retries=3,
        )
        self._agent = create_react_agent(
            model=self._llm,
            tools=self._tools,
            prompt=_SYSTEM_PROMPT,
        )

    async def setup(self) -> None:
        """Initialise the MCP client, load tools, and create the ReAct agent."""
        mcp_config = build_mcp_config(self._settings)
        self._mcp_client = MultiServerMCPClient(mcp_config)
        self._tools = await self._mcp_client.get_tools()
        self._rebuild_agent_with_model(self._current_model)

    async def chat(self, message: str) -> str:
        """Run the agent with a user message and return the response text.

        Features automated model failover: if one model runs into a rate limit
        or quota exhaustion, OmniPlus immediately shifts to the next available
        Gemini model and completes the request seamlessly!
        """
        if self._agent is None:
            raise RuntimeError("MCPAssistant.setup() must be called before chat().")

        self._history.append(("human", message))

        # Try across the model pool
        last_error = None
        for attempt in range(len(self._model_pool)):
            active_model = self._model_pool[self._current_model_idx]
            try:
                result = await self._agent.ainvoke({"messages": self._history})
                # Succeeded! Process and return response
                messages = result.get("messages", []) if result else []
                if messages:
                    last = messages[-1]
                    raw = last.content if hasattr(last, "content") else (last.get("content") if isinstance(last, dict) else "")
                    if isinstance(raw, list):
                        parts = []
                        for item in raw:
                            if isinstance(item, dict) and "text" in item:
                                parts.append(item["text"])
                            elif isinstance(item, str):
                                parts.append(item)
                            elif hasattr(item, "text"):
                                parts.append(str(item.text))
                        content = "\n".join(parts) if parts else str(raw)
                    else:
                        content = str(raw) if raw else "(No response)"
                    self._history.append(("assistant", content))
                    return content
                return "(No response)"

            except Exception as exc:
                err_text = str(exc)
                last_error = exc
                is_quota_or_limit = (
                    "429" in err_text
                    or "RESOURCE_EXHAUSTED" in err_text
                    or "rate_limit" in err_text.lower()
                    or "quota" in err_text.lower()
                    or "404" in err_text
                    or "NOT_FOUND" in err_text
                )

                if is_quota_or_limit and attempt < len(self._model_pool) - 1:
                    # Switch to next model in pool
                    self._current_model_idx = (self._current_model_idx + 1) % len(self._model_pool)
                    next_model = self._model_pool[self._current_model_idx]
                    self._rebuild_agent_with_model(next_model)
                    await asyncio.sleep(1.0)
                    continue
                elif not is_quota_or_limit:
                    raise exc

        # If all models in the pool failed
        return (
            "⏳ **Google AI Studio Free Tier daily quota reached on available models.**\n\n"
            "Please wait a few minutes before trying again, or generate a fresh free Gemini API key at "
            "[Google AI Studio](https://aistudio.google.com/app/apikey)."
        )

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
