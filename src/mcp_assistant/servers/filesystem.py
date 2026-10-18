"""Filesystem MCP server configuration.

Wraps the `mcp-server-filesystem` npx package and exposes a config dict
compatible with langchain-mcp-adapters MultiServerMCPClient.
"""
from __future__ import annotations

import os
from pathlib import Path


class FilesystemServer:
    """Configuration provider for the MCP filesystem server.

    The underlying server is `@modelcontextprotocol/server-filesystem`, run
    via ``npx``.  It exposes tools such as read_file, list_directory,
    search_files, and get_file_info over MCP's stdio transport.

    Args:
        base_path: The root directory the server is allowed to access.
            Defaults to the current user's home directory.
    """

    def __init__(self, base_path: str | Path | None = None) -> None:
        if base_path is None:
            base_path = Path.home()
        self.base_path = str(Path(base_path).expanduser().resolve())

    def get_server_config(self) -> dict:
        """Return the MCP server config dict for MultiServerMCPClient.

        The config uses the stdio transport and passes the base_path as a
        positional argument to mcp-server-filesystem so it only has access
        to that directory tree.

        Returns:
            A dict with keys ``command``, ``args``, and ``transport``.
        """
        return {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                self.base_path,
            ],
            "transport": "stdio",
        }
