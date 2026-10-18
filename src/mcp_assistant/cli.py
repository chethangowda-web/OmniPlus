"""CLI entry point for the MCP AI Assistant.

Commands
--------
mcp-assistant chat   - Start an interactive REPL session.
mcp-assistant run    - Run a single query non-interactively.
mcp-assistant tools  - List all available MCP tools.
"""
from __future__ import annotations

import asyncio
import sys

import click
from rich.console import Console
from rich.prompt import Prompt

from mcp_assistant.ui.display import (
    print_error,
    print_response,
    print_thinking,
    print_tool_list,
    print_welcome_banner,
)

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Run an async coroutine in a new event loop (compatible with Python 3.11+)."""
    return asyncio.run(coro)


async def _build_assistant():
    """Instantiate and set up the MCPAssistant, returning it ready to use."""
    from mcp_assistant.config import get_settings
    from mcp_assistant.assistant import MCPAssistant

    settings = get_settings()
    assistant = MCPAssistant(settings)
    await assistant.setup()
    return assistant


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(package_name="mcp-ai-assistant")
def main() -> None:
    """MCP AI Assistant — a local AI CLI powered by Google Gemini and MCP."""


# ---------------------------------------------------------------------------
# chat command
# ---------------------------------------------------------------------------

@main.command()
def chat() -> None:
    """Start an interactive REPL chat session with the AI assistant."""

    async def _chat_loop() -> None:
        print_welcome_banner()

        try:
            with print_thinking("Connecting to MCP servers…") as status:
                assistant = await _build_assistant()
                status.update("[bold green]Connected! All MCP servers are ready.[/bold green]")

            tool_count = len(assistant.get_tool_names())
            console.print(
                f"[dim]Loaded [bold cyan]{tool_count}[/bold cyan] MCP tools. "
                f"Type [bold red]exit[/bold red] to quit.[/dim]\n"
            )
        except EnvironmentError as exc:
            print_error(str(exc))
            sys.exit(1)
        except Exception as exc:  # noqa: BLE001
            print_error(f"Failed to initialise assistant: {exc}")
            sys.exit(1)

        try:
            while True:
                try:
                    user_input = Prompt.ask("[bold cyan]You[/bold cyan]").strip()
                except (EOFError, KeyboardInterrupt):
                    break

                if not user_input:
                    continue
                if user_input.lower() in {"exit", "quit", "bye", ":q"}:
                    break

                try:
                    with print_thinking("Thinking…"):
                        response = await assistant.chat(user_input)
                    print_response(response)
                except Exception as exc:  # noqa: BLE001
                    print_error(f"Error during chat: {exc}")
        finally:
            await assistant.close()
            console.print("\n[bold blue]Goodbye! 👋[/bold blue]\n")

    try:
        _run_async(_chat_loop())
    except KeyboardInterrupt:
        console.print("\n[bold blue]Goodbye! 👋[/bold blue]\n")


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------

@main.command()
@click.option(
    "--prompt", "-p",
    required=True,
    help="The query to send to the assistant.",
)
def run(prompt: str) -> None:
    """Run a single query non-interactively and print the response."""

    async def _run_once() -> None:
        try:
            with print_thinking("Connecting to MCP servers…"):
                assistant = await _build_assistant()
        except EnvironmentError as exc:
            print_error(str(exc))
            sys.exit(1)
        except Exception as exc:  # noqa: BLE001
            print_error(f"Failed to initialise assistant: {exc}")
            sys.exit(1)

        try:
            with print_thinking("Thinking…"):
                response = await assistant.chat(prompt)
            print_response(response)
        except Exception as exc:  # noqa: BLE001
            print_error(f"Error: {exc}")
        finally:
            await assistant.close()

    try:
        _run_async(_run_once())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interrupted.[/bold yellow]\n")


# ---------------------------------------------------------------------------
# tools command
# ---------------------------------------------------------------------------

@main.command()
def tools() -> None:
    """List all available MCP tools loaded from enabled servers."""

    async def _list_tools() -> None:
        try:
            with print_thinking("Loading MCP tools…"):
                assistant = await _build_assistant()
        except EnvironmentError as exc:
            print_error(str(exc))
            sys.exit(1)
        except Exception as exc:  # noqa: BLE001
            print_error(f"Failed to initialise assistant: {exc}")
            sys.exit(1)

        tool_names = assistant.get_tool_names()
        print_tool_list(tool_names)
        await assistant.close()

    try:
        _run_async(_list_tools())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
