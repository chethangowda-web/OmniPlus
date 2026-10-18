# OmniPlus 🤖✨

**OmniPlus** is an MCP-powered local AI assistant CLI that connects Google Gemini to your real-world tools, local files, live web search, and GitHub repositories using the Model Context Protocol (MCP).

## Features

- 🧠 **Google Gemini AI** — Powered by `gemini-2.0-flash` for fast, intelligent reasoning
- 📁 **Files & Documents** — Read, search, list, and summarize local files and directories via MCP
- 🌐 **Web Search** — Real-time internet search using DuckDuckGo FastMCP (or Brave Search)
- 🐙 **Code Repositories** — Query GitHub repos, issues, pull requests, and source code
- 💬 **Interactive REPL** — Rich terminal TUI with syntax-highlighted markdown, spinners, and slash commands (`/help`, `/tools`, `/clear`, `/exit`)
- 📜 **Multi-turn Memory** — Context-aware conversation history with automatic session persistence
- 🔄 **ReAct Agent** — LangGraph ReAct agent pattern for multi-step reasoning and dynamic tool execution

## Architecture

```
OmniPlus/
├── src/mcp_assistant/
│   ├── cli.py              # Click-based CLI entry point (omniplus chat / run / tools / config)
│   ├── config.py           # Settings and environment configuration (.env)
│   ├── assistant.py        # Core MCPAssistant with LangGraph + MultiServerMCPClient
│   ├── servers/            # MCP server configurations
│   │   ├── filesystem.py   # Local file system MCP server (npx)
│   │   ├── websearch.py    # Web search MCP server selector
│   │   ├── _ddg_server.py  # DuckDuckGo FastMCP stdio server
│   │   ├── github.py       # GitHub MCP server (npx)
│   │   └── config_builder.py  # MultiServerMCPClient config aggregator
│   └── ui/
│       └── display.py      # Rich TUI helpers
└── pyproject.toml
```

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+ (required for npx-based MCP servers)
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### Steps

1. **Clone the repository**

   ```bash
   git clone https://github.com/chethangowda-web/OmniPlus.git
   cd OmniPlus
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv .venv
   # On Linux/macOS:
   source .venv/bin/activate
   # On Windows:
   .venv\Scripts\activate
   ```

3. **Install the package**

   ```bash
   pip install -e .
   ```

4. **Set up your environment**

   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

   Required:
   - `GEMINI_API_KEY` — Your Google Gemini API key

   Optional:
   - `GITHUB_TOKEN` — GitHub personal access token (for GitHub integration)
   - `GITLAB_TOKEN` — GitLab personal access token (for GitLab integration)
   - `GITLAB_URL` — GitLab instance URL (defaults to `https://gitlab.com`)

## Usage

### Interactive Chat Mode

Start an interactive REPL session with the AI assistant:

```bash
mcp-assistant chat
```

Example session:

```
You: Summarize the README.md in my current directory
Assistant: Here's a summary of your README.md...

You: Search the web for latest Python 3.13 features
Assistant: I found the following information...

You: Show me open issues in my GitHub repo owner/repo
Assistant: Here are the open issues...
```

### Single Query Mode

Run a single query non-interactively (great for scripting):

```bash
mcp-assistant run --prompt "List all Python files in ~/projects/myapp"
```

### List Available Tools

See all MCP tools currently loaded:

```bash
mcp-assistant tools
```

## Configuration

All configuration is done via environment variables in the `.env` file:

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | — | Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model name |
| `GITHUB_TOKEN` | No | — | GitHub personal access token |
| `GITLAB_TOKEN` | No | — | GitLab personal access token |
| `GITLAB_URL` | No | `https://gitlab.com` | GitLab instance URL |

## MCP Servers

| Server | Tool | Requires |
|---|---|---|
| Filesystem | `mcp-server-filesystem` (npx) | Node.js |
| Web Search | `@modelcontextprotocol/server-brave-search` or DuckDuckGo | Node.js / Python |
| GitHub | `@modelcontextprotocol/server-github` (npx) | Node.js + `GITHUB_TOKEN` |

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License — see [LICENSE](LICENSE) for details.
