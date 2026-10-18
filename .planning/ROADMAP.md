# MCP AI Assistant — Roadmap

## Milestone 0.1.0 — MVP

---

### Phase 1: Core Setup & CLI Shell ✅
**Goal**: Get a working Gemini-powered chat loop with a beautiful Rich CLI.

### Phase 2: Filesystem MCP Integration ✅
**Goal**: Let the assistant read, search, and summarise local files.

### Phase 3: Web Search Integration ✅
**Goal**: Give the assistant real-time web search capabilities.

### Phase 4: GitHub / GitLab MCP Integration ✅
**Goal**: Allow querying GitHub repositories, issues, and code.

### Phase 5: Polish & UX ✅
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
