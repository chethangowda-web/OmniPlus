# MCP AI Assistant 🤖

An MCP-powered local AI assistant CLI that uses Google Gemini as the AI model, with integrations for local file systems, web search, GitHub, and GitLab.

## Features

- 🧠 **Google Gemini AI** — Powered by `gemini-2.0-flash` for fast, intelligent responses
- 📁 **File System Integration** — Read, search, list, and summarize local files and directories via MCP
- 🌐 **Web Search** — Search the web using DuckDuckGo (or Brave Search) through an MCP server
- 🐙 **GitHub Integration** — Browse repositories, issues, PRs, and code via the GitHub MCP server
- 🦊 **GitLab Integration** — Access GitLab repositories and resources via MCP
- 💻 **Rich CLI** — Beautiful terminal UI using the `rich` library with markdown rendering and spinners
- 🔄 **ReAct Agent** — Uses LangChain's ReAct agent pattern for multi-step reasoning and tool use

## Architecture

```
mcp-ai-assistant/
├── src/mcp_assistant/
│   ├── cli.py              # Click-based CLI entry point
│   ├── config.py           # Settings and environment configuration
│   ├── assistant.py        # Core MCPAssistant with LangChain + MCP
│   ├── servers/            # MCP server configurations
│   │   ├── filesystem.py   # Local file system MCP server
│   │   ├── websearch.py    # Web search MCP server
│   │   ├── github.py       # GitHub MCP server
│   │   └── config_builder.py  # Builds MultiServerMCPClient config
│   └── ui/
│       └── display.py      # Rich UI helpers
└── pyproject.toml
```

The assistant uses the **Model Context Protocol (MCP)** to connect to external tools and data sources. Each integration is a separate MCP server, and LangChain's `MultiServerMCPClient` manages connections to all of them. The ReAct agent dynamically selects which tools to call based on the user's query.

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+ (required for npx-based MCP servers)
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### Steps

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/mcp-ai-assistant.git
   cd mcp-ai-assistant
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
