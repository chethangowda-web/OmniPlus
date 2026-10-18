"""Builds the MultiServerMCPClient configuration from application settings.

Determines which MCP servers are enabled based on which credentials are
available, then returns a unified config dict that can be passed directly
to ``langchain_mcp_adapters.client.MultiServerMCPClient``.
"""
from __future__ import annotations

from mcp_assistant.config import Settings
from mcp_assistant.servers.filesystem import FilesystemServer
from mcp_assistant.servers.github import GitHubServer
from mcp_assistant.servers.websearch import WebSearchServer


def build_mcp_config(settings: Settings) -> dict[str, dict]:
    """Build the MultiServerMCPClient config from the current settings.

    Servers included:
    - ``filesystem``: Always enabled. Scoped to the user's home directory.
    - ``websearch``: Always enabled. Uses Brave Search if BRAVE_API_KEY is set,
      otherwise falls back to DuckDuckGo.
    - ``github``: Enabled only when ``settings.github_token`` is set.

    Args:
        settings: The application Settings instance.

    Returns:
        A mapping of server name → server config dict, ready to be passed to
        ``MultiServerMCPClient``.
    """
    config: dict[str, dict] = {}

    # --- Filesystem (always on) ---
    config["filesystem"] = FilesystemServer().get_server_config()

    # --- Web search (always on) ---
    config["websearch"] = WebSearchServer().get_server_config()

    # --- GitHub (only if token present) ---
    if settings.has_github():
        config["github"] = GitHubServer(
            github_token=settings.github_token  # type: ignore[arg-type]
        ).get_server_config()

    return config
