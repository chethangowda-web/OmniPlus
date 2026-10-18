# MCP AI Assistant — Roadmap

## Milestone 0.1.0 — MVP

---

### Phase 1: Core Setup & CLI Shell ✅
**Goal**: Get a working Gemini-powered chat loop with a beautiful Rich CLI.

**Deliverables**:
- `pyproject.toml` with all dependencies
- `config.py` with Settings dataclass and `.env` loading
- `cli.py` with `chat`, `run`, and `tools` commands
- `assistant.py` stub (Gemini LLM, no MCP tools yet)
- `ui/display.py` with Rich banner, spinner, response panel, error panel
- Basic `mcp-assistant chat` interactive loop working end-to-end

**Success Criteria**:
- `mcp-assistant chat` opens a prompt and echoes Gemini responses
- `mcp-assistant run --prompt "Hello"` works non-interactively
- Missing `GEMINI_API_KEY` shows a clear error

---

### Phase 2: Filesystem MCP Integration
**Goal**: Let the assistant read, search, and summarise local files.

**Deliverables**:
- `servers/filesystem.py` — `FilesystemServer` wrapping `mcp-server-filesystem`
- `servers/config_builder.py` — always enables the filesystem server
- Integration test: ask the assistant to read a known file
- Node.js / npx availability check with helpful error message

**Success Criteria**:
- `mcp-assistant chat` then "summarise ~/Documents/notes.txt" works correctly
- `mcp-assistant tools` lists filesystem tools (read_file, list_directory, etc.)

---

### Phase 3: Web Search Integration
**Goal**: Give the assistant real-time web search capabilities.

**Deliverables**:
- `servers/_ddg_server.py` — standalone DuckDuckGo MCP server (stdio)
- `servers/websearch.py` — `WebSearchServer` (Brave preferred, DDG fallback)
- Update `config_builder.py` to include websearch always

**Success Criteria**:
- "What is the latest version of Python?" returns an up-to-date answer
- Works without any additional API keys (DDG fallback)
- Brave Search used automatically when `BRAVE_API_KEY` is set

---

### Phase 4: GitHub / GitLab MCP Integration
**Goal**: Allow querying GitHub repositories, issues, and code.

**Deliverables**:
- `servers/github.py` — `GitHubServer` wrapping `@modelcontextprotocol/server-github`
- Update `config_builder.py` to enable GitHub when `GITHUB_TOKEN` is set
- GitLab server config (optional, future)
- Documentation for required token scopes

**Success Criteria**:
- "List open issues in owner/repo" returns real data
- "Show me the README of owner/repo" works
- Assistant gracefully skips GitHub tools when no token is configured

---

### Phase 5: Polish & UX
**Goal**: Make the CLI delightful to use with streaming, history, and improved output.

**Deliverables**:
- Streaming token output (real-time response display) using LangChain callbacks
- Conversation history / multi-turn context (LangGraph memory)
- Session history saved to `~/.mcp-assistant/history.json`
- `/help` and `/tools` slash commands within the chat REPL
- Colour-coded tool call indicators (shows which tool was invoked)
- `mcp-assistant config` command to display current settings

**Success Criteria**:
- Responses stream token-by-token in the terminal
- Prior conversation context is remembered within a session
- `mcp-assistant --version` and `--help` work correctly

---

## Future Milestones

- **0.2.0** — Plugin system: custom MCP servers loaded from `~/.mcp-assistant/servers/`
- **0.3.0** — Web UI (FastAPI + HTMX) alongside the CLI
- **1.0.0** — Production hardening, comprehensive test suite, PyPI release
