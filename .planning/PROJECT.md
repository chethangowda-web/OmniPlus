# MCP AI Assistant — Project Context

## Project Name
MCP AI Assistant

## Description
A local AI assistant CLI that integrates the **Model Context Protocol (MCP)** with **Google Gemini** to provide intelligent, tool-augmented responses. Users can ask the assistant to read local files, search the web, and explore GitHub repositories — all through natural language.

## Goals
- Provide a seamless, conversational interface to local files and external services.
- Demonstrate the power of MCP as a universal tool-integration standard for AI agents.
- Be fully local-first: no cloud data storage, all processing through the user's own API keys.

## Tech Stack
| Layer | Technology |
|---|---|
| AI Model | Google Gemini (`gemini-2.0-flash`) via `langchain-google-genai` |
| Agent Framework | LangChain + LangGraph ReAct agent |
| Tool Protocol | Model Context Protocol (MCP) via `langchain-mcp-adapters` |
| CLI Interface | Click + Rich |
| Language | Python 3.11+ |
| Build System | Hatchling (`pyproject.toml`) |

## Key Integrations
| Integration | MCP Server | Auth Required |
|---|---|---|
| Local Filesystem | `@modelcontextprotocol/server-filesystem` (npx) | None |
| Web Search | DuckDuckGo (bundled) / Brave Search (npx) | Optional: `BRAVE_API_KEY` |
| GitHub | `@modelcontextprotocol/server-github` (npx) | `GITHUB_TOKEN` |

## Architecture Overview
```
User (CLI)
    │
    ▼
cli.py  (Click commands: chat / run / tools)
    │
    ▼
assistant.py  (MCPAssistant — LangChain ReAct agent)
    │
    ├── langchain-google-genai  →  Gemini LLM
    │
    └── langchain-mcp-adapters  →  MultiServerMCPClient
            │
            ├── MCP Server: filesystem   (npx)
            ├── MCP Server: websearch    (Python / npx)
            └── MCP Server: github       (npx, if token set)
```

## Configuration
All secrets are managed via a `.env` file. See `.env.example` for the full list of supported variables.
