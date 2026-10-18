"""GitHub MCP server configuration.

Wraps `@modelcontextprotocol/server-github` via npx and provides a config
dict compatible with langchain-mcp-adapters MultiServerMCPClient.
"""
from __future__ import annotations


class GitHubServer:
    """Configuration provider for the GitHub MCP server.

    Requires a valid ``GITHUB_TOKEN`` to be passed in so the underlying
    server can authenticate with the GitHub API.

    Args:
        github_token: A GitHub personal access token (classic or fine-grained)
            with the scopes needed for your intended operations (e.g. ``repo``,
            ``read:org``).
    """

    def __init__(self, github_token: str) -> None:
        if not github_token:
            raise ValueError("github_token must not be empty.")
        self.github_token = github_token

    def get_server_config(self) -> dict:
        """Return the MCP server config dict for MultiServerMCPClient.

        The GitHub token is forwarded to the server process via an environment
        variable so it never appears in command-line arguments.

        Returns:
            A dict with keys ``command``, ``args``, ``env``, and ``transport``.
        """
        return {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-github",
            ],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token,
            },
            "transport": "stdio",
        }
