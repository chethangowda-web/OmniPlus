"""FastAPI Web Server for OmniPlus AI Assistant."""
from __future__ import annotations

import asyncio
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from mcp_assistant.config import get_settings
from mcp_assistant.assistant import MCPAssistant
from mcp_assistant.servers.config_builder import build_mcp_config

app = FastAPI(title="OmniPlus AI Assistant", version="0.1.0")

# Global assistant singleton for web session
_assistant_instance: MCPAssistant | None = None
_init_lock = asyncio.Lock()


async def get_or_create_assistant() -> MCPAssistant:
    global _assistant_instance
    if _assistant_instance is not None:
        return _assistant_instance

    async with _init_lock:
        if _assistant_instance is not None:
            return _assistant_instance
        try:
            settings = get_settings()
            assistant = MCPAssistant(settings)
            await assistant.setup()
            _assistant_instance = assistant
            return _assistant_instance
        except EnvironmentError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize assistant: {e}")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    tools: list[str]


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "OmniPlus"}


@app.get("/api/config")
async def get_config_info():
    try:
        settings = get_settings()
        servers = build_mcp_config(settings)
        return {
            "model": settings.gemini_model,
            "has_github": settings.has_github(),
            "enabled_servers": list(servers.keys()),
        }
    except Exception as e:
        return {"error": str(e), "model": "gemini-2.0-flash", "enabled_servers": ["filesystem", "websearch"]}


@app.get("/api/tools")
async def get_tools():
    try:
        assistant = await get_or_create_assistant()
        return {"tools": assistant.get_tool_names()}
    except HTTPException:
        raise
    except Exception as e:
        return {"tools": [], "error": str(e)}


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    assistant = await get_or_create_assistant()
    try:
        reply = await assistant.chat(req.message.strip())
        return ChatResponse(response=reply, tools=assistant.get_tool_names())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clear")
async def clear_history():
    if _assistant_instance is not None:
        _assistant_instance.clear_history()
    return {"status": "cleared"}


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_CONTENT


HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OmniPlus — MCP-Powered AI Assistant</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    :root {
      --bg: #090d16;
      --card-bg: rgba(17, 24, 39, 0.75);
      --border: rgba(255, 255, 255, 0.1);
      --primary: #6366f1;
      --primary-glow: rgba(99, 102, 241, 0.35);
      --accent: #8b5cf6;
      --cyan: #06b6d4;
      --text: #f3f4f6;
      --text-dim: #9ca3af;
      --user-bubble: #1e1b4b;
      --assistant-bubble: rgba(30, 41, 59, 0.85);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
      background: radial-gradient(circle at 10% 20%, #17153b 0%, var(--bg) 60%),
                  radial-gradient(circle at 90% 80%, #0e2a47 0%, transparent 50%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      backdrop-filter: blur(16px);
      background: rgba(9, 13, 22, 0.7);
      border-bottom: 1px solid var(--border);
      padding: 1rem 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .brand-icon {
      width: 40px;
      height: 40px;
      border-radius: 12px;
      background: linear-gradient(135deg, #6366f1, #a855f7);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.25rem;
      box-shadow: 0 0 20px var(--primary-glow);
    }
    .brand h1 {
      font-size: 1.35rem;
      font-weight: 800;
      background: linear-gradient(135deg, #fff, #c7d2fe);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .badge {
      font-size: 0.72rem;
      padding: 0.2rem 0.55rem;
      border-radius: 20px;
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(99, 102, 241, 0.35);
      color: #a5b4fc;
      font-weight: 600;
      letter-spacing: 0.03em;
    }
    .integrations {
      display: flex;
      gap: 0.5rem;
      align-items: center;
    }
    .tool-chip {
      font-size: 0.78rem;
      display: flex;
      align-items: center;
      gap: 0.35rem;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.3rem 0.65rem;
      color: var(--text-dim);
    }
    .main-container {
      flex: 1;
      max-width: 960px;
      width: 100%;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      padding: 1.5rem;
      height: calc(100vh - 73px);
    }
    .chat-box {
      flex: 1;
      overflow-y: auto;
      padding-right: 0.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      margin-bottom: 1rem;
    }
    .chat-box::-webkit-scrollbar {
      width: 6px;
    }
    .chat-box::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.15);
      border-radius: 3px;
    }
    .msg {
      display: flex;
      gap: 0.85rem;
      max-width: 85%;
      animation: fadeIn 0.25s ease-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .msg.user {
      align-self: flex-end;
      flex-direction: row-reverse;
    }
    .msg.assistant {
      align-self: flex-start;
    }
    .avatar {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.1rem;
      flex-shrink: 0;
    }
    .msg.user .avatar {
      background: #4338ca;
    }
    .msg.assistant .avatar {
      background: linear-gradient(135deg, #0ea5e9, #6366f1);
      box-shadow: 0 0 15px rgba(14, 165, 233, 0.3);
    }
    .bubble {
      padding: 0.95rem 1.25rem;
      border-radius: 16px;
      font-size: 0.94rem;
      line-height: 1.55;
    }
    .msg.user .bubble {
      background: var(--user-bubble);
      border: 1px solid rgba(99, 102, 241, 0.35);
      color: #e0e7ff;
      border-top-right-radius: 4px;
    }
    .msg.assistant .bubble {
      background: var(--assistant-bubble);
      border: 1px solid var(--border);
      color: var(--text);
      border-top-left-radius: 4px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .bubble pre {
      background: #0d1117;
      border: 1px solid rgba(255, 255, 255, 0.1);
      padding: 0.75rem 1rem;
      border-radius: 8px;
      overflow-x: auto;
      margin: 0.75rem 0;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85rem;
    }
    .bubble code {
      font-family: 'JetBrains Mono', monospace;
      background: rgba(255, 255, 255, 0.1);
      padding: 0.15rem 0.35rem;
      border-radius: 4px;
      font-size: 0.85rem;
    }
    .bubble pre code {
      background: none;
      padding: 0;
    }
    .bubble p:not(:last-child) {
      margin-bottom: 0.65rem;
    }
    .input-wrapper {
      background: var(--card-bg);
      border: 1px solid var(--border);
      backdrop-filter: blur(12px);
      border-radius: 16px;
      padding: 0.75rem;
      display: flex;
      gap: 0.5rem;
      align-items: center;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
    }
    .input-wrapper input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: #fff;
      font-size: 0.95rem;
      padding: 0.4rem 0.6rem;
      font-family: inherit;
    }
    .input-wrapper input::placeholder {
      color: var(--text-dim);
    }
    .btn {
      background: linear-gradient(135deg, var(--primary), var(--accent));
      color: white;
      border: none;
      outline: none;
      border-radius: 10px;
      padding: 0.65rem 1.25rem;
      font-weight: 600;
      font-size: 0.9rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      transition: all 0.2s ease;
      box-shadow: 0 4px 14px var(--primary-glow);
    }
    .btn:hover {
      opacity: 0.92;
      transform: translateY(-1px);
    }
    .btn:active {
      transform: translateY(0);
    }
    .btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none;
    }
    .btn-secondary {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border);
      box-shadow: none;
      color: var(--text-dim);
      padding: 0.65rem 0.85rem;
    }
    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.12);
      color: #fff;
    }
    .welcome-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 2rem;
      text-align: center;
      margin: auto 0;
      max-width: 650px;
      align-self: center;
    }
    .welcome-card h2 {
      font-size: 1.6rem;
      font-weight: 700;
      margin-bottom: 0.6rem;
      background: linear-gradient(135deg, #a5b4fc, #38bdf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .welcome-card p {
      color: var(--text-dim);
      font-size: 0.95rem;
      line-height: 1.6;
      margin-bottom: 1.5rem;
    }
    .suggestions {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 0.75rem;
      text-align: left;
    }
    .suggestion-btn {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.75rem 1rem;
      color: #cbd5e1;
      font-size: 0.85rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .suggestion-btn:hover {
      background: rgba(99, 102, 241, 0.12);
      border-color: rgba(99, 102, 241, 0.4);
      color: #fff;
    }
    .spinner {
      display: inline-block;
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-radius: 50%;
      border-top-color: #fff;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="brand-icon">🤖</div>
      <div>
        <h1>OmniPlus</h1>
      </div>
      <span class="badge">MCP Assistant</span>
    </div>
    <div class="integrations">
      <div class="tool-chip">📁 Files</div>
      <div class="tool-chip">🌐 Search</div>
      <div class="tool-chip">🐙 GitHub</div>
      <button class="btn btn-secondary" onclick="clearChat()" title="Clear chat history">🧹 Clear</button>
    </div>
  </header>

  <div class="main-container">
    <div class="chat-box" id="chatBox">
      <div class="welcome-card" id="welcomeCard">
        <h2>What would you like to explore today?</h2>
        <p>OmniPlus connects Google Gemini directly to your local files, web searches, and code repositories via Model Context Protocol (MCP).</p>
        <div class="suggestions">
          <button class="suggestion-btn" onclick="sendSuggestion('What is the latest version of Python and its top features?')">
            🌐 <b>Search web</b><br>Latest Python version & features
          </button>
          <button class="suggestion-btn" onclick="sendSuggestion('List the files and directories in the current folder.')">
            📁 <b>Inspect Files</b><br>List files in this project
          </button>
          <button class="suggestion-btn" onclick="sendSuggestion('Explain how the Model Context Protocol (MCP) works.')">
            🧠 <b>Ask Gemini</b><br>How MCP works
          </button>
          <button class="suggestion-btn" onclick="sendSuggestion('List the tools currently available in this session.')">
            🔧 <b>Check Tools</b><br>Show active MCP tools
          </button>
        </div>
      </div>
    </div>

    <div class="input-wrapper">
      <input type="text" id="userInput" placeholder="Ask OmniPlus or prompt a tool action... (Press Enter)" autofocus />
      <button class="btn" id="sendBtn" onclick="sendMessage()">
        <span>Send</span>
        <span>➤</span>
      </button>
    </div>
  </div>

  <script>
    const chatBox = document.getElementById('chatBox');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const welcomeCard = document.getElementById('welcomeCard');

    userInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        sendMessage();
      }
    });

    function sendSuggestion(text) {
      userInput.value = text;
      sendMessage();
    }

    async function sendMessage() {
      const text = userInput.value.trim();
      if (!text) return;

      if (welcomeCard) {
        welcomeCard.style.display = 'none';
      }

      appendMessage('user', text);
      userInput.value = '';
      sendBtn.disabled = true;
      sendBtn.innerHTML = '<span class="spinner"></span> Thinking...';

      const loadingMsg = appendMessage('assistant', '<span class="spinner"></span> <i>OmniPlus is thinking & calling MCP tools...</i>');

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Error contacting assistant');
        }
        loadingMsg.querySelector('.bubble').innerHTML = marked.parse(data.response);
      } catch (err) {
        loadingMsg.querySelector('.bubble').innerHTML = `<p style="color: #f87171;">⚠️ <b>Error:</b> ${err.message}</p>`;
      } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<span>Send</span> <span>➤</span>';
        chatBox.scrollTop = chatBox.scrollHeight;
        userInput.focus();
      }
    }

    function appendMessage(role, contentHtml) {
      const msg = document.createElement('div');
      msg.className = `msg ${role}`;
      msg.innerHTML = `
        <div class="avatar">${role === 'user' ? '👤' : '🤖'}</div>
        <div class="bubble">${contentHtml.startsWith('<') ? contentHtml : `<p>${contentHtml}</p>`}</div>
      `;
      chatBox.appendChild(msg);
      chatBox.scrollTop = chatBox.scrollHeight;
      return msg;
    }

    async function clearChat() {
      await fetch('/api/clear', { method: 'POST' });
      chatBox.innerHTML = '';
      if (welcomeCard) {
        chatBox.appendChild(welcomeCard);
        welcomeCard.style.display = 'block';
      }
    }
  </script>
</body>
</html>
"""


def run_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the FastAPI application via uvicorn."""
    uvicorn.run("mcp_assistant.web.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run_server()
