"""Web search MCP server configuration.

Tries to use `@modelcontextprotocol/server-brave-search` (if a BRAVE_API_KEY
is found in the environment) and falls back to a lightweight custom DuckDuckGo
MCP server implemented in Python using the `duckduckgo-search` package.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


class WebSearchServer:
    """Configuration provider for the web search MCP server.

    Strategy:
    1. If ``BRAVE_API_KEY`` is set, use the official Brave Search MCP server
       (npx-based).
    2. Otherwise fall back to the bundled DuckDuckGo MCP server script, which
       uses the ``duckduckgo-search`` Python package — no extra API key needed.

    Args:
        brave_api_key: Optional Brave Search API key. When provided the Brave
            server is preferred.
    """

    def __init__(self, brave_api_key: str | None = None) -> None:
        self.brave_api_key = brave_api_key or os.getenv("BRAVE_API_KEY")

    def get_server_config(self) -> dict:
        """Return the MCP server config dict for MultiServerMCPClient.

        Returns:
            A dict with keys ``command``, ``args``, ``env`` (optional), and
            ``transport``.
        """
        if self.brave_api_key:
            return self._brave_config()
        return self._duckduckgo_config()

    def _brave_config(self) -> dict:
        return {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-brave-search",
            ],
            "env": {
                "BRAVE_API_KEY": self.brave_api_key,
            },
            "transport": "stdio",
        }

    def _duckduckgo_config(self) -> dict:
        """Use the bundled DuckDuckGo server script shipped with this package."""
        # The helper script lives next to this file.
        ddg_script = Path(__file__).parent / "_ddg_server.py"
        return {
            "command": sys.executable,
            "args": [str(ddg_script)],
            "transport": "stdio",
        }
