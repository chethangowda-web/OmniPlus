"""Standalone DuckDuckGo MCP server (stdio transport).

This script is launched as a subprocess by WebSearchServer when no Brave API
key is configured. It exposes a single MCP tool — ``web_search`` — that
queries DuckDuckGo and returns a structured list of results.

Run directly (for debugging):
    python _ddg_server.py
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from duckduckgo_search import DDGS
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
)


app = Server("duckduckgo-search")


@app.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(
        tools=[
            Tool(
                name="web_search",
                description=(
                    "Search the web using DuckDuckGo. Returns a list of results "
                    "with title, url, and snippet for each result."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query.",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default 5).",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            )
        ]
    )


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    if name != "web_search":
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")],
            isError=True,
        )

    query: str = arguments.get("query", "")
    max_results: int = int(arguments.get("max_results", 5))

    if not query:
        return CallToolResult(
            content=[TextContent(type="text", text="Query must not be empty.")],
            isError=True,
        )

    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))

        formatted = []
        for r in raw_results:
            formatted.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
            )

        output = json.dumps(formatted, indent=2, ensure_ascii=False)
        return CallToolResult(
            content=[TextContent(type="text", text=output)],
            isError=False,
        )
    except Exception as exc:  # noqa: BLE001
        return CallToolResult(
            content=[TextContent(type="text", text=f"Search failed: {exc}")],
            isError=True,
        )


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
