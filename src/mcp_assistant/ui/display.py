"""Rich UI helpers for the MCP AI Assistant CLI."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()


def print_welcome_banner() -> None:
    """Print a stylised welcome banner."""
    banner_text = Text()
    banner_text.append("OmniPlus AI Assistant", style="bold cyan")
    banner_text.append("  🤖✨", style="white")
    banner_text.append("\n\nPowered by ", style="dim white")
    banner_text.append("Google Gemini", style="bold green")
    banner_text.append(" + ", style="dim white")
    banner_text.append("Model Context Protocol", style="bold magenta")
    banner_text.append("\n\nIntegrations: ", style="dim white")
    banner_text.append("📁 Files  🌐 Web Search  🐙 GitHub  🦊 GitLab", style="yellow")
    banner_text.append("\n\nType ", style="dim white")
    banner_text.append("exit", style="bold red")
    banner_text.append(" or press ", style="dim white")
    banner_text.append("Ctrl+C", style="bold red")
    banner_text.append(" to quit.", style="dim white")

    panel = Panel(
        banner_text,
        title="[bold blue]Welcome[/bold blue]",
        border_style="blue",
        box=box.DOUBLE_EDGE,
        expand=False,
        padding=(1, 4),
    )
    console.print()
    console.print(panel)
    console.print()


def print_tool_list(tools: list[str]) -> None:
    """Print the list of available MCP tools as a rich table.

    Args:
        tools: List of tool name strings.
    """
    table = Table(
        title="[bold cyan]Available MCP Tools[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold magenta",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Tool Name", style="bold green", min_width=30)

    for idx, tool_name in enumerate(sorted(tools), start=1):
        table.add_row(str(idx), tool_name)

    if not tools:
        table.add_row("—", "[italic dim]No tools loaded[/italic dim]")

    console.print()
    console.print(table)
    console.print(f"\n[dim]Total: {len(tools)} tool(s)[/dim]")
    console.print()


@contextmanager
def print_thinking(message: str = "Thinking...") -> Generator[Status, None, None]:
    """Context manager that shows a spinner while the assistant is working.

    Args:
        message: Status message to display beside the spinner.

    Yields:
        The rich Status object (can be updated via status.update()).
    """
    with console.status(f"[bold yellow]{message}[/bold yellow]", spinner="dots") as status:
        yield status


def print_response(response: str) -> None:
    """Render and print the AI response with markdown formatting.

    Args:
        response: The assistant's response text (may contain markdown).
    """
    md = Markdown(response)
    panel = Panel(
        md,
        title="[bold green]Assistant[/bold green]",
        border_style="green",
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print()
    console.print(panel)
    console.print()


def print_error(error: str) -> None:
    """Print an error message in red.

    Args:
        error: The error message to display.
    """
    panel = Panel(
        f"[bold red]{error}[/bold red]",
        title="[bold red]Error[/bold red]",
        border_style="red",
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print()
    console.print(panel)
    console.print()


def print_tool_call(tool_name: str) -> None:
    """Print an indicator when a tool is being called.

    Args:
        tool_name: The name of the MCP tool being invoked.
    """
    console.print(f"  [dim]🔧 Using tool: [bold magenta]{tool_name}[/bold magenta][/dim]")
