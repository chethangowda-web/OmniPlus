"""FastAPI Web Server for OmniPlus AI Assistant — Full Power Dashboard."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

from mcp_assistant.config import get_settings
from mcp_assistant.assistant import MCPAssistant
from mcp_assistant.servers.config_builder import build_mcp_config

app = FastAPI(title="OmniPlus AI Assistant", version="0.2.0")

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


class SettingsUpdateRequest(BaseModel):
    provider: str | None = None
    groq_model: str | None = None
    groq_api_key: str | None = None
    gemini_model: str | None = None
    gemini_api_key: str | None = None
    model: str | None = None
    api_key: str | None = None


def _update_env_file(key_values: dict[str, str]) -> None:
    """Safely persist updated configuration keys to the local .env file."""
    env_path = Path(".env")
    lines: list[str] = []
    existing_keys: set[str] = set()

    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            line_s = line.strip()
            if "=" in line_s and not line_s.startswith("#"):
                k, _ = line_s.split("=", 1)
                k = k.strip()
                if k in key_values:
                    lines[i] = f"{k}={key_values[k]}"
                    existing_keys.add(k)

    for k, v in key_values.items():
        if k not in existing_keys and v:
            lines.append(f"{k}={v}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@app.get("/api/health")
async def health():
    try:
        settings = get_settings()
        prov = settings.get_active_provider()
        model = settings.groq_model if prov == "groq" else settings.gemini_model
    except Exception:
        prov = "groq"
        model = "llama-3.3-70b-versatile"
    return {
        "status": "ok",
        "app": "OmniPlus",
        "version": "0.3.0",
        "provider": prov,
        "model": model,
        "python": os.sys.version.split()[0],
    }


@app.get("/api/config")
async def get_config_info():
    try:
        settings = get_settings()
        servers = build_mcp_config(settings)
        active_prov = settings.get_active_provider()
        return {
            "provider": active_prov,
            "groq_model": settings.groq_model,
            "has_groq": settings.has_groq(),
            "gemini_model": settings.gemini_model,
            "has_gemini": settings.has_gemini(),
            "has_github": settings.has_github(),
            "enabled_servers": list(servers.keys()),
            "groq_key_masked": (
                f"{settings.groq_api_key[:6]}...{settings.groq_api_key[-4:]}"
                if settings.has_groq() and len(settings.groq_api_key or "") > 10
                else ("Configured" if settings.has_groq() else "Not set")
            ),
            "gemini_key_masked": (
                f"{settings.gemini_api_key[:6]}...{settings.gemini_api_key[-4:]}"
                if settings.has_gemini() and len(settings.gemini_api_key) > 10
                else ("Configured" if settings.has_gemini() else "Not set")
            ),
            "model": settings.groq_model if active_prov == "groq" else settings.gemini_model,
        }
    except Exception as e:
        return {
            "error": str(e),
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "has_groq": False,
            "has_gemini": False,
            "enabled_servers": ["filesystem", "websearch"],
        }


@app.post("/api/settings/update")
async def update_settings(req: SettingsUpdateRequest):
    global _assistant_instance
    updates: dict[str, str] = {}

    if req.provider:
        p = req.provider.strip().lower()
        updates["LLM_PROVIDER"] = p
        os.environ["LLM_PROVIDER"] = p
    if req.groq_model:
        updates["GROQ_MODEL"] = req.groq_model.strip()
        os.environ["GROQ_MODEL"] = req.groq_model.strip()
    if req.groq_api_key and req.groq_api_key.strip():
        updates["GROQ_API_KEY"] = req.groq_api_key.strip()
        os.environ["GROQ_API_KEY"] = req.groq_api_key.strip()
    if req.gemini_model:
        updates["GEMINI_MODEL"] = req.gemini_model.strip()
        os.environ["GEMINI_MODEL"] = req.gemini_model.strip()
    if req.gemini_api_key and req.gemini_api_key.strip():
        updates["GEMINI_API_KEY"] = req.gemini_api_key.strip()
        os.environ["GEMINI_API_KEY"] = req.gemini_api_key.strip()

    # Backwards compatibility
    if req.model:
        if "gemini" in req.model.lower():
            updates["GEMINI_MODEL"] = req.model.strip()
            os.environ["GEMINI_MODEL"] = req.model.strip()
        else:
            updates["GROQ_MODEL"] = req.model.strip()
            os.environ["GROQ_MODEL"] = req.model.strip()
    if req.api_key and req.api_key.strip():
        if req.api_key.strip().startswith("gsk_"):
            updates["GROQ_API_KEY"] = req.api_key.strip()
            os.environ["GROQ_API_KEY"] = req.api_key.strip()
        else:
            updates["GEMINI_API_KEY"] = req.api_key.strip()
            os.environ["GEMINI_API_KEY"] = req.api_key.strip()

    if updates:
        _update_env_file(updates)

    get_settings.cache_clear()
    settings = get_settings()
    _assistant_instance = MCPAssistant(settings)
    await _assistant_instance.setup()

    return {
        "status": "updated",
        "provider": _assistant_instance.provider,
        "model": _assistant_instance.current_model,
        "has_groq": settings.has_groq(),
        "has_gemini": settings.has_gemini(),
    }


@app.get("/api/tools")
async def get_tools():
    try:
        assistant = await get_or_create_assistant()
        return {"tools": assistant.get_tool_names()}
    except HTTPException:
        raise
    except Exception as e:
        return {"tools": [], "error": str(e)}


@app.get("/api/tools/detailed")
async def get_tools_detailed():
    try:
        assistant = await get_or_create_assistant()
        return {"tools": assistant.get_tool_details()}
    except Exception as e:
        return {"tools": [], "error": str(e)}


@app.get("/api/files/tree")
async def get_files_tree():
    """Scan and return the current project directory structure safely."""
    def build_tree(path: str, max_depth: int = 3, cur_depth: int = 0):
        if cur_depth > max_depth:
            return []
        items = []
        try:
            for entry in sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower())):
                if entry.name in {'.git', '.venv', '__pycache__', 'dist', 'build', '.idea', 'node_modules'}:
                    continue
                rel_path = os.path.relpath(entry.path, ".").replace("\\", "/")
                if entry.is_dir():
                    items.append({
                        "name": entry.name,
                        "type": "dir",
                        "path": rel_path,
                        "children": build_tree(entry.path, max_depth, cur_depth + 1)
                    })
                else:
                    items.append({
                        "name": entry.name,
                        "type": "file",
                        "path": rel_path,
                        "size": entry.stat().st_size
                    })
        except Exception:
            pass
        return items

    return {"root": "OmniPlus Workspace", "tree": build_tree(".")}


@app.get("/api/files/content")
async def get_file_content(path: str):
    """Safely read and return file contents."""
    norm_path = os.path.normpath(path)
    if norm_path.startswith("..") or os.path.isabs(norm_path):
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.exists(norm_path) or not os.path.isfile(norm_path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with open(norm_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(60000)
        return {
            "path": norm_path.replace("\\", "/"),
            "content": content,
            "size": os.path.getsize(norm_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search")
async def run_web_search(q: str):
    """Run direct DuckDuckGo search."""
    if not q or not q.strip():
        return {"query": "", "results": []}
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(q.strip(), max_results=8))
        return {"query": q, "results": results}
    except Exception as e:
        return {"query": q, "results": [], "error": str(e)}


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


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """Server-Sent Events endpoint for real-time token and tool streaming."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    assistant = await get_or_create_assistant()

    async def event_generator():
        try:
            async for ev in assistant.stream_chat(req.message.strip()):
                yield f"data: {json.dumps(ev)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
  <title>OmniPlus — MCP Assistant</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github-dark.min.css">
  <script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js"></script>
  <style>
    :root {
      --bg: #070913;
      --surface: #0c101d;
      --card-bg: #0f1527;
      --card-hover: #141c33;
      --border: rgba(255, 255, 255, 0.08);
      --border-focus: rgba(99, 102, 241, 0.5);
      --primary: #4f46e5;
      --primary-light: #6366f1;
      --primary-gradient: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
      --accent: #a855f7;
      --cyan: #06b6d4;
      --emerald: #10b981;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --glow-blue: rgba(14, 165, 233, 0.25);
      --glow-purple: rgba(124, 58, 237, 0.3);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Plus Jakarta Sans', sans-serif;
      background-color: var(--bg);
      color: var(--text);
      min-height: 100vh;
      overflow-x: hidden;
      display: flex;
      flex-direction: column;
    }

    /* TOP NAVBAR */
    .top-nav {
      height: 64px;
      padding: 0 1.5rem;
      background: rgba(10, 14, 26, 0.85);
      backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      cursor: pointer;
    }
    .brand-logo {
      width: 38px;
      height: 38px;
      border-radius: 12px;
      background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 20px rgba(99, 102, 241, 0.4);
    }
    .brand-title {
      font-size: 1.25rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #fff;
    }
    .badge-pill {
      font-size: 0.72rem;
      font-weight: 600;
      padding: 0.2rem 0.6rem;
      border-radius: 20px;
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(99, 102, 241, 0.35);
      color: #a5b4fc;
      margin-left: 0.25rem;
    }
    .nav-right {
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }
    .status-pill {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.35rem 0.8rem;
      border-radius: 20px;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
    }
    .status-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 10px #10b981;
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(0.85); }
    }
    .nav-btn {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border);
      padding: 0.4rem 0.8rem;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .nav-btn:hover {
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
      border-color: rgba(255, 255, 255, 0.15);
    }
    .nav-btn.danger { color: #f87171; }
    .nav-btn.danger:hover {
      background: rgba(239, 68, 68, 0.12);
      border-color: rgba(239, 68, 68, 0.3);
    }

    /* APP LAYOUT */
    .app-layout {
      flex: 1;
      display: grid;
      grid-template-columns: 210px 1fr 280px;
      gap: 1.25rem;
      padding: 1.25rem;
      max-width: 1680px;
      margin: 0 auto;
      width: 100%;
      height: calc(100vh - 64px);
      overflow: hidden;
    }

    /* LEFT SIDEBAR */
    .sidebar-left {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      height: 100%;
    }
    .nav-menu {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }
    .nav-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.65rem 0.95rem;
      border-radius: 12px;
      font-size: 0.9rem;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.2s ease;
      text-decoration: none;
    }
    .nav-item:hover {
      background: rgba(255, 255, 255, 0.04);
      color: #fff;
    }
    .nav-item.active {
      background: #2e266d;
      color: #fff;
      box-shadow: 0 4px 16px rgba(67, 56, 202, 0.35);
    }
    .nav-item svg {
      width: 18px;
      height: 18px;
      opacity: 0.85;
    }
    .nav-item.active svg {
      opacity: 1;
      color: #a5b4fc;
    }

    /* INSPIRATION MINI CARD (SIDEBAR BOTTOM) */
    .promo-card {
      background: linear-gradient(145deg, #161538 0%, #0d1224 100%);
      border: 1px solid rgba(99, 102, 241, 0.2);
      border-radius: 16px;
      padding: 1rem;
      position: relative;
      overflow: hidden;
      margin-bottom: 0.75rem;
    }
    .promo-card h4 {
      font-size: 0.82rem;
      font-weight: 700;
      color: #fff;
      line-height: 1.35;
      margin-bottom: 0.25rem;
    }
    .promo-card p {
      font-size: 0.72rem;
      color: var(--text-dim);
    }
    .promo-mountain {
      margin-top: 0.5rem;
      width: 100%;
      height: 65px;
      display: block;
    }
    .user-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.65rem 0.8rem;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border);
      border-radius: 12px;
      cursor: pointer;
    }
    .user-info {
      display: flex;
      align-items: center;
      gap: 0.55rem;
    }
    .user-avatar {
      width: 28px;
      height: 28px;
      border-radius: 8px;
      background: linear-gradient(135deg, #06b6d4, #3b82f6);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
    }
    .user-text h5 {
      font-size: 0.76rem;
      font-weight: 700;
      color: #fff;
    }
    .user-text span {
      font-size: 0.68rem;
      color: var(--text-dim);
    }

    /* CENTER WORKSPACE */
    .center-workspace {
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow-y: auto;
      padding-right: 0.35rem;
      gap: 1.25rem;
      position: relative;
    }
    .center-workspace::-webkit-scrollbar {
      width: 6px;
    }
    .center-workspace::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 4px;
    }

    /* DEDICATED VIEW CONTAINERS */
    .view-container {
      display: none;
      flex-direction: column;
      gap: 1.25rem;
      flex: 1;
      animation: fadeIn 0.2s ease-out;
    }
    .view-container.active-view {
      display: flex;
    }

    /* HERO BANNER */
    .hero-banner {
      background: radial-gradient(circle at 85% 30%, #1e1b4b 0%, #0c1228 50%, #080c1b 100%);
      border: 1px solid rgba(99, 102, 241, 0.25);
      border-radius: 20px;
      padding: 2rem 2.25rem;
      position: relative;
      overflow: hidden;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.45);
    }
    .hero-banner::before {
      content: '';
      position: absolute;
      top: -50px;
      right: 15%;
      width: 320px;
      height: 320px;
      background: radial-gradient(circle, rgba(14, 165, 233, 0.15), transparent 70%);
      pointer-events: none;
    }
    .hero-content {
      max-width: 58%;
      z-index: 2;
    }
    .hero-title {
      font-size: 2rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      margin-bottom: 0.6rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .hero-title .wave {
      animation: wave 1.8s infinite;
      display: inline-block;
      transform-origin: 70% 70%;
    }
    @keyframes wave {
      0%, 100% { transform: rotate(0deg); }
      20%, 60% { transform: rotate(14deg); }
      40%, 80% { transform: rotate(-10deg); }
    }
    .hero-title span {
      background: linear-gradient(135deg, #a5b4fc 0%, #38bdf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
      font-size: 0.95rem;
      color: var(--text-muted);
      line-height: 1.55;
      margin-bottom: 1.5rem;
    }
    .hero-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.6rem;
    }
    .hero-action-pill {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 0.55rem 0.9rem;
      display: flex;
      align-items: center;
      gap: 0.6rem;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .hero-action-pill:hover {
      background: rgba(99, 102, 241, 0.15);
      border-color: rgba(99, 102, 241, 0.4);
      transform: translateY(-2px);
    }
    .pill-icon { font-size: 1.15rem; }
    .pill-text h5 { font-size: 0.8rem; font-weight: 700; color: #fff; }
    .pill-text p { font-size: 0.68rem; color: var(--text-dim); }

    .hero-art {
      width: 250px;
      height: 180px;
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1;
    }
    .planet-glow {
      position: absolute;
      top: -20px;
      right: 20px;
      width: 140px;
      height: 140px;
      border-radius: 50%;
      background: radial-gradient(circle at 35% 35%, #60a5fa 0%, #2563eb 50%, #1e1b4b 100%);
      box-shadow: 0 0 50px rgba(59, 130, 246, 0.5), inset 0 0 25px rgba(255, 255, 255, 0.4);
    }
    .robot-cliff {
      position: absolute;
      bottom: 0;
      right: 10px;
      width: 180px;
      height: 140px;
    }

    /* EXPLORE SECTION */
    .explore-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.85rem;
    }
    .explore-title-group {
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
    }
    .explore-title {
      font-size: 1.15rem;
      font-weight: 800;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 0.45rem;
    }
    .explore-subtitle {
      font-size: 0.8rem;
      color: var(--text-dim);
    }
    .mcp-status-tag {
      font-size: 0.72rem;
      font-weight: 700;
      color: #34d399;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.35);
      border-radius: 20px;
      padding: 0.25rem 0.65rem;
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }
    .mcp-status-tag .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10b981;
    }

    /* 4 FEATURE CARDS */
    .features-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
    }
    .feature-card {
      background: #0d1222;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      padding: 1.25rem 1rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 220px;
      cursor: pointer;
      transition: all 0.25s ease;
    }
    .feature-card:hover {
      background: #12182e;
      border-color: rgba(99, 102, 241, 0.4);
      transform: translateY(-4px);
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
    }
    .card-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.85rem;
    }
    .card-icon-wrap {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.1rem;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
    }
    .card-illustration {
      width: 72px;
      height: 52px;
      opacity: 0.85;
      transition: all 0.3s ease;
    }
    .feature-card:hover .card-illustration {
      transform: scale(1.08);
      opacity: 1;
    }
    .card-body h4 { font-size: 0.95rem; font-weight: 700; color: #fff; margin-bottom: 0.2rem; }
    .card-tag { font-size: 0.65rem; font-weight: 700; color: #818cf8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; display: inline-block; }
    .card-body p { font-size: 0.74rem; color: var(--text-muted); line-height: 1.45; }
    .card-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 1rem;
      padding-top: 0.65rem;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
    .arrow-btn {
      width: 28px;
      height: 28px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.06);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #a5b4fc;
      font-size: 0.85rem;
      transition: all 0.2s;
    }
    .feature-card:hover .arrow-btn { background: var(--primary); color: #fff; transform: translateX(3px); }

    /* CONVERSATION DRAWER (STREAMING) */
    .chat-drawer {
      display: none;
      flex-direction: column;
      gap: 1rem;
      background: #0a0e1c;
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 1.25rem;
      max-height: 480px;
      overflow-y: auto;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }
    .chat-drawer.open { display: flex; }
    .drawer-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.75rem;
    }
    .drawer-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }
    .drawer-controls {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .mini-btn {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 0.3rem 0.65rem;
      border-radius: 8px;
      font-size: 0.72rem;
      font-weight: 600;
      cursor: pointer;
    }
    .mini-btn:hover { background: rgba(255, 255, 255, 0.1); color: #fff; }

    /* STREAMING MESSAGES */
    .msg-group { display: flex; flex-direction: column; gap: 1rem; }
    .msg { display: flex; gap: 0.75rem; max-width: 90%; animation: fadeIn 0.2s ease-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
    .msg.user { align-self: flex-end; flex-direction: row-reverse; }
    .msg.assistant { align-self: flex-start; }
    .msg-avatar {
      width: 32px;
      height: 32px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.95rem;
      flex-shrink: 0;
    }
    .msg.user .msg-avatar { background: #4338ca; }
    .msg.assistant .msg-avatar { background: linear-gradient(135deg, #0ea5e9, #6366f1); box-shadow: 0 0 15px rgba(14, 165, 233, 0.35); }
    .msg-bubble {
      padding: 0.85rem 1.15rem;
      border-radius: 16px;
      font-size: 0.9rem;
      line-height: 1.55;
      position: relative;
    }
    .msg.user .msg-bubble { background: #1e1b4b; border: 1px solid rgba(99, 102, 241, 0.3); color: #e0e7ff; border-top-right-radius: 4px; }
    .msg.assistant .msg-bubble { background: #11172a; border: 1px solid var(--border); color: var(--text); border-top-left-radius: 4px; width: 100%; }

    /* TOOL CALL BADGE IN CHAT */
    .tool-badge-pill {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(99, 102, 241, 0.35);
      color: #a5b4fc;
      border-radius: 12px;
      padding: 0.3rem 0.65rem;
      font-size: 0.75rem;
      font-family: 'JetBrains Mono', monospace;
      margin-bottom: 0.6rem;
      animation: pulseGlow 1.5s infinite;
    }
    @keyframes pulseGlow { 0%, 100% { border-color: rgba(99, 102, 241, 0.35); } 50% { border-color: #818cf8; } }

    /* SYNTAX CODE BLOCK WITH COPY BUTTON */
    .code-container {
      position: relative;
      margin: 0.75rem 0;
    }
    .code-container pre {
      background: #090c16;
      border: 1px solid rgba(255, 255, 255, 0.08);
      padding: 1rem;
      border-radius: 10px;
      overflow-x: auto;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.83rem;
    }
    .code-copy-btn {
      position: absolute;
      top: 8px;
      right: 8px;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border);
      color: #cbd5e1;
      padding: 0.25rem 0.55rem;
      border-radius: 6px;
      font-size: 0.7rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .code-copy-btn:hover { background: #4f46e5; color: #fff; }

    /* FLOATING CHAT INPUT BAR WITH SPEECH MIC */
    .chat-input-bar {
      margin-top: auto;
      background: #0e1428;
      border: 1px solid rgba(99, 102, 241, 0.3);
      border-radius: 30px;
      padding: 0.45rem 0.65rem 0.45rem 1.25rem;
      display: flex;
      align-items: center;
      gap: 0.6rem;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(99, 102, 241, 0.15);
      position: sticky;
      bottom: 0;
      z-index: 50;
    }
    .chat-sparkle { font-size: 1.15rem; color: #a855f7; }
    .chat-input-bar input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      font-size: 0.92rem;
      color: #fff;
      font-family: inherit;
    }
    .chat-input-bar input::placeholder { color: var(--text-dim); }
    .mic-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      font-size: 1.1rem;
      padding: 0.3rem 0.5rem;
      border-radius: 50%;
      transition: all 0.2s;
    }
    .mic-btn:hover { color: #fff; background: rgba(255, 255, 255, 0.05); }
    .mic-btn.listening {
      color: #ef4444;
      animation: pulse 1s infinite;
    }
    .send-pill-btn {
      background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
      color: #fff;
      border: none;
      outline: none;
      padding: 0.55rem 1.25rem;
      border-radius: 20px;
      font-weight: 700;
      font-size: 0.86rem;
      display: flex;
      align-items: center;
      gap: 0.35rem;
      cursor: pointer;
      transition: all 0.2s ease;
      box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);
    }
    .send-pill-btn:hover { opacity: 0.92; transform: scale(1.02); }
    .send-pill-btn:disabled { opacity: 0.4; cursor: not-allowed; }

    /* DEDICATED PANELS (FILES, SEARCH, TOOLS, GITHUB, SETTINGS) */
    .view-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }
    .view-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .view-title { font-size: 1.2rem; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 0.5rem; }

    /* FILE TREE VIEW */
    .file-explorer {
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: 1rem;
      min-height: 400px;
    }
    .tree-pane {
      background: #090c16;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 0.85rem;
      overflow-y: auto;
      max-height: 500px;
    }
    .tree-item {
      padding: 0.35rem 0.55rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.82rem;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 0.45rem;
    }
    .tree-item:hover { background: rgba(255, 255, 255, 0.05); color: #fff; }
    .tree-item.selected { background: #2e266d; color: #fff; }
    .code-viewer-pane {
      background: #090c16;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    .code-viewer-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.5rem;
    }
    .code-pre-box {
      flex: 1;
      overflow: auto;
      max-height: 420px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.82rem;
      color: #e2e8f0;
      white-space: pre-wrap;
    }

    /* WEB SEARCH EXPLORER */
    .search-input-box {
      display: flex;
      gap: 0.65rem;
    }
    .search-bar {
      flex: 1;
      background: #090c16;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.75rem 1rem;
      color: #fff;
      font-family: inherit;
      outline: none;
    }
    .search-results-grid {
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
      max-height: 500px;
      overflow-y: auto;
    }
    .search-card {
      background: #090c16;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1rem;
      transition: all 0.2s;
    }
    .search-card:hover { border-color: rgba(99, 102, 241, 0.4); transform: translateY(-2px); }
    .search-card h4 { font-size: 0.95rem; color: #60a5fa; margin-bottom: 0.2rem; }
    .search-card a { font-size: 0.72rem; color: var(--text-dim); text-decoration: none; word-break: break-all; }
    .search-card p { font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem; line-height: 1.45; }

    /* TOOLS PLAYGROUND */
    .tools-list-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1rem;
    }
    .tool-box-card {
      background: #090c16;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .tool-box-card h4 { font-size: 0.9rem; color: #34d399; margin-bottom: 0.4rem; font-family: 'JetBrains Mono', monospace; }
    .tool-box-card p { font-size: 0.76rem; color: var(--text-muted); line-height: 1.4; margin-bottom: 0.75rem; }

    /* SETTINGS VIEW */
    .settings-form {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      max-width: 600px;
    }
    .form-group { display: flex; flex-direction: column; gap: 0.4rem; }
    .form-label { font-size: 0.82rem; font-weight: 600; color: #cbd5e1; }
    .form-input {
      background: #090c16;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.65rem 0.9rem;
      color: #fff;
      font-family: inherit;
    }

    /* RIGHT SIDEBAR */
    .sidebar-right {
      display: flex;
      flex-direction: column;
      gap: 1.1rem;
      height: 100%;
      overflow-y: auto;
    }
    .sidebar-right::-webkit-scrollbar { width: 4px; }
    .sidebar-right::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 4px; }
    .panel-box {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 1.1rem;
    }
    .panel-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.85rem; }
    .panel-title { font-size: 0.88rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 0.4rem; }
    .panel-desc { font-size: 0.72rem; color: var(--text-dim); margin-top: -0.5rem; margin-bottom: 0.75rem; }
    .action-row { display: flex; align-items: center; justify-content: space-between; padding: 0.65rem 0.6rem; border-radius: 10px; cursor: pointer; transition: all 0.2s; }
    .action-row:hover { background: rgba(255, 255, 255, 0.04); }
    .action-left { display: flex; align-items: center; gap: 0.65rem; }
    .action-icon { width: 32px; height: 32px; border-radius: 8px; background: rgba(255, 255, 255, 0.04); display: flex; align-items: center; justify-content: center; font-size: 0.95rem; }
    .action-meta h5 { font-size: 0.8rem; font-weight: 700; color: #fff; }
    .action-meta p { font-size: 0.68rem; color: var(--text-dim); }
    .chevron-right { color: var(--text-dim); font-size: 0.85rem; transition: all 0.2s; }
    .action-row:hover .chevron-right { color: #fff; transform: translateX(2px); }

    /* ACTIVITY STREAM */
    .activity-list { display: flex; flex-direction: column; gap: 0.5rem; }
    .activity-item { display: flex; align-items: center; gap: 0.65rem; padding: 0.5rem 0.4rem; border-radius: 8px; }
    .activity-icon { width: 28px; height: 28px; border-radius: 7px; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; flex-shrink: 0; }
    .icon-blue { background: rgba(14, 165, 233, 0.15); color: #38bdf8; }
    .icon-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
    .icon-purple { background: rgba(168, 85, 247, 0.15); color: #c084fc; }
    .icon-green { background: rgba(16, 185, 129, 0.15); color: #34d399; }
    .activity-text h6 { font-size: 0.77rem; font-weight: 600; color: #e2e8f0; }
    .activity-text span { font-size: 0.67rem; color: var(--text-dim); }

    .promo-mountain-card {
      background: linear-gradient(135deg, #131433 0%, #0c1228 100%);
      border: 1px solid rgba(99, 102, 241, 0.2);
      border-radius: 16px;
      padding: 1.1rem;
      position: relative;
      overflow: hidden;
      margin-top: auto;
    }
    .promo-mountain-card h4 { font-size: 0.88rem; font-weight: 700; color: #fff; margin-bottom: 0.15rem; }
    .promo-mountain-card p { font-size: 0.72rem; color: var(--text-muted); }
    .promo-mountain-card svg { width: 100%; height: 70px; margin-top: 0.5rem; }
  </style>
</head>
<body>

  <!-- TOP HEADER -->
  <header class="top-nav">
    <div class="brand" onclick="switchView('home')">
      <div class="brand-logo">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2">
          <rect x="3" y="11" width="18" height="10" rx="2"></rect>
          <circle cx="12" cy="5" r="2"></circle>
          <path d="M12 7v4"></path>
          <line x1="8" y1="16" x2="8.01" y2="16"></line>
          <line x1="16" y1="16" x2="16.01" y2="16"></line>
        </svg>
      </div>
      <h1 class="brand-title">OmniPlus</h1>
      <span class="badge-pill">MCP Assistant</span>
    </div>

    <div class="nav-right">
      <div class="status-pill">
        <span class="status-dot"></span>
        <span id="navModelStatus">Ready • gemini-3.5-flash</span>
      </div>
      <button class="nav-btn" onclick="switchView('files')">
        <span>📁</span> Files
      </button>
      <button class="nav-btn" onclick="switchView('search')">
        <span>🌐</span> Search
      </button>
      <button class="nav-btn" onclick="switchView('github')">
        <span>🐙</span> GitHub
      </button>
      <button class="nav-btn" onclick="exportConversation()" title="Export chat history as markdown">
        <span>📥</span> Export
      </button>
      <button class="nav-btn danger" onclick="clearAllChat()">
        <span>🧹</span> Clear
      </button>
    </div>
  </header>

  <!-- MAIN APP CONTAINER -->
  <div class="app-layout">

    <!-- LEFT SIDEBAR -->
    <aside class="sidebar-left">
      <div class="nav-menu">
        <a class="nav-item active" id="nav-home" href="#" onclick="switchView('home')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
          <span>Home</span>
        </a>
        <a class="nav-item" id="nav-files" href="#" onclick="switchView('files')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
          <span>Files</span>
        </a>
        <a class="nav-item" id="nav-search" href="#" onclick="switchView('search')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          <span>Search</span>
        </a>
        <a class="nav-item" id="nav-github" href="#" onclick="switchView('github')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>
          <span>GitHub</span>
        </a>
        <a class="nav-item" id="nav-tools" href="#" onclick="switchView('tools')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>
          <span>Tools</span>
        </a>
        <a class="nav-item" id="nav-settings" href="#" onclick="switchView('settings')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
          <span>Settings</span>
        </a>
      </div>

      <div>
        <!-- INSPIRATION MOUNTAIN CARD -->
        <div class="promo-card">
          <h4>Small steps<br>build big things ✨</h4>
          <p>Keep exploring!</p>
          <svg class="promo-mountain" viewBox="0 0 180 65" fill="none">
            <polygon points="10,65 50,22 85,65" fill="#1e1b4b" opacity="0.6"/>
            <polygon points="65,65 110,12 155,65" fill="#312e81" opacity="0.8"/>
            <polygon points="40,65 95,16 145,65" fill="url(#gradMount)"/>
            <circle cx="110" cy="11" r="2.5" fill="#f43f5e"/>
            <line x1="110" y1="11" x2="110" y2="18" stroke="#f43f5e" stroke-width="1.2"/>
            <polygon points="110,11 118,13 110,16" fill="#f43f5e"/>
            <defs>
              <linearGradient id="gradMount" x1="95" y1="16" x2="95" y2="65" gradientUnits="userSpaceOnUse">
                <stop stop-color="#4f46e5"/>
                <stop offset="1" stop-color="#0e1428"/>
              </linearGradient>
            </defs>
          </svg>
        </div>

        <!-- USER STATUS FOOTER -->
        <div class="user-footer" onclick="switchView('settings')">
          <div class="user-info">
            <div class="user-avatar">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
            </div>
            <div class="user-text">
              <h5>MCP Connected</h5>
              <span>OmniPlus</span>
            </div>
          </div>
          <span style="color: var(--text-dim); font-size: 0.85rem;">›</span>
        </div>
      </div>
    </aside>

    <!-- CENTER WORKSPACE -->
    <main class="center-workspace">

      <!-- VIEW 1: HOME DASHBOARD -->
      <div class="view-container active-view" id="view-home">
        <!-- HERO BANNER -->
        <section class="hero-banner">
          <div class="hero-content">
            <h2 class="hero-title">
              <span class="wave">👋</span> Good <span id="timeGreeting">morning</span>, <span>Explorer!</span>
            </h2>
            <p class="hero-subtitle">
              Your AI-powered workspace is ready. Ask OmniPlus anything or explore your tools to get started.
            </p>

            <div class="hero-actions">
              <div class="hero-action-pill" onclick="quickPrompt('Search the web for top trending AI frameworks in 2026.')">
                <span class="pill-icon">🌐</span>
                <div class="pill-text">
                  <h5>Search the web</h5>
                  <p>Get latest info & docs</p>
                </div>
              </div>

              <div class="hero-action-pill" onclick="quickPrompt('Inspect and summarize the files in this workspace.')">
                <span class="pill-icon">📁</span>
                <div class="pill-text">
                  <h5>Inspect files</h5>
                  <p>Explore your project</p>
                </div>
              </div>

              <div class="hero-action-pill" onclick="quickPrompt('Explain how OmniPlus utilizes the Model Context Protocol.')">
                <span class="pill-icon">✨</span>
                <div class="pill-text">
                  <h5>Ask Gemini</h5>
                  <p>Use MCP tools</p>
                </div>
              </div>

              <div class="hero-action-pill" onclick="quickPrompt('List all active MCP tools and demonstrate one.')">
                <span class="pill-icon">🔧</span>
                <div class="pill-text">
                  <h5>Run tools</h5>
                  <p>Execute MCP actions</p>
                </div>
              </div>
            </div>
          </div>

          <!-- COSMIC PLANET + ROBOT GRAPHIC -->
          <div class="hero-art">
            <div class="planet-glow"></div>
            <svg class="robot-cliff" viewBox="0 0 200 160" fill="none">
              <path d="M0 160 L50 115 L110 90 L160 110 L200 160 Z" fill="#0c1228" opacity="0.95"/>
              <path d="M70 160 L120 85 L180 120 L200 160 Z" fill="#141935" opacity="0.85"/>
              <path d="M95 105 L155 100 L185 160 L75 160 Z" fill="#080b18"/>
              <g transform="translate(125, 60)">
                <rect x="10" y="2" width="22" height="18" rx="6" fill="#e2e8f0"/>
                <rect x="13" y="6" width="16" height="9" rx="3" fill="#0f172a"/>
                <ellipse cx="17" cy="10" rx="1.8" ry="2.2" fill="#38bdf8"/>
                <ellipse cx="25" cy="10" rx="1.8" ry="2.2" fill="#38bdf8"/>
                <line x1="21" y1="2" x2="21" y2="-4" stroke="#94a3b8" stroke-width="1.8"/>
                <circle cx="21" cy="-5" r="2" fill="#818cf8"/>
                <rect x="8" y="22" width="26" height="24" rx="7" fill="#cbd5e1"/>
                <circle cx="21" cy="32" r="4.5" fill="#38bdf8" opacity="0.8"/>
                <rect x="4" y="42" width="16" height="7" rx="3" fill="#94a3b8"/>
                <rect x="22" y="42" width="16" height="7" rx="3" fill="#94a3b8"/>
                <polygon points="26,38 42,38 40,44 24,44" fill="#64748b"/>
                <polygon points="34,26 44,26 42,38 32,38" fill="#38bdf8" opacity="0.9"/>
                <ellipse cx="33" cy="40" rx="8" ry="2" fill="#38bdf8" opacity="0.6"/>
              </g>
            </svg>
          </div>
        </section>

        <!-- EXPLORE WITH OMNIPLUS SECTION -->
        <section>
          <div class="explore-header">
            <div class="explore-title-group">
              <h3 class="explore-title">
                <span style="color: #a855f7;">✨</span> Explore with OmniPlus
              </h3>
              <p class="explore-subtitle">Powerful tools, all in one place. Choose what you want to do.</p>
            </div>

            <div class="mcp-status-tag">
              <span class="dot"></span>
              <span>MCP Connected</span>
            </div>
          </div>

          <!-- 4 FEATURE CARDS -->
          <div class="features-grid">
            <div class="feature-card" onclick="quickPrompt('Search the web for Model Context Protocol news.')">
              <div>
                <div class="card-top">
                  <div class="card-icon-wrap" style="color: #38bdf8;">🔍</div>
                  <svg class="card-illustration" viewBox="0 0 80 60" fill="none">
                    <circle cx="45" cy="30" r="24" stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="3 3" opacity="0.7"/>
                    <ellipse cx="45" cy="30" rx="24" ry="10" stroke="#38bdf8" stroke-width="1.2" opacity="0.8"/>
                    <ellipse cx="45" cy="30" rx="10" ry="24" stroke="#38bdf8" stroke-width="1.2" opacity="0.8"/>
                    <circle cx="58" cy="22" r="3" fill="#0ea5e9"/>
                  </svg>
                </div>
                <div class="card-body">
                  <h4>Search Web</h4>
                  <span class="card-tag">MCP</span>
                  <p>Get the latest information, docs, and real-time data from the web.</p>
                </div>
              </div>
              <div class="card-footer">
                <span style="font-size: 0.72rem; color: var(--text-dim);">DuckDuckGo & Brave</span>
                <div class="arrow-btn">→</div>
              </div>
            </div>

            <div class="feature-card" onclick="switchView('files')">
              <div>
                <div class="card-top">
                  <div class="card-icon-wrap" style="color: #34d399;">📁</div>
                  <svg class="card-illustration" viewBox="0 0 80 60" fill="none">
                    <path d="M20 22 C20 18, 22 16, 26 16 L38 16 L44 22 L68 22 C72 22, 74 24, 74 28 L74 46 C74 50, 72 52, 68 52 L26 52 C22 52, 20 50, 20 46 Z" fill="#065f46" opacity="0.6"/>
                    <path d="M12 28 C12 24, 14 22, 18 22 L30 22 L36 28 L60 28 C64 28, 66 30, 66 34 L66 52 C66 56, 64 58, 60 58 L18 58 C14 58, 12 56, 12 52 Z" fill="#047857" opacity="0.8"/>
                    <path d="M8 34 C8 30, 10 28, 14 28 L26 28 L32 34 L54 34 C58 34, 60 36, 60 40 L60 56 C60 60, 58 62, 54 62 L14 62 C10 62, 8 60, 8 56 Z" fill="#10b981"/>
                  </svg>
                </div>
                <div class="card-body">
                  <h4>Inspect Files</h4>
                  <span class="card-tag">MCP</span>
                  <p>Read, analyze and explore your project files and structure.</p>
                </div>
              </div>
              <div class="card-footer">
                <span style="font-size: 0.72rem; color: var(--text-dim);">Filesystem MCP</span>
                <div class="arrow-btn">→</div>
              </div>
            </div>

            <div class="feature-card" onclick="quickPrompt('How can I use OmniPlus to optimize my software development?')">
              <div>
                <div class="card-top">
                  <div class="card-icon-wrap" style="color: #c084fc;">✨</div>
                  <svg class="card-illustration" viewBox="0 0 80 60" fill="none">
                    <path d="M50 10 L53 22 L65 25 L53 28 L50 40 L47 28 L35 25 L47 22 Z" fill="#c084fc"/>
                    <path d="M26 28 L28 35 L35 37 L28 39 L26 46 L24 39 L17 37 L24 35 Z" fill="#a855f7" opacity="0.75"/>
                  </svg>
                </div>
                <div class="card-body">
                  <h4>Ask Gemini</h4>
                  <span class="card-tag">MCP</span>
                  <p>Get intelligent responses using Google Gemini and MCP tools.</p>
                </div>
              </div>
              <div class="card-footer">
                <span style="font-size: 0.72rem; color: var(--text-dim);">Multi-Model Failover</span>
                <div class="arrow-btn">→</div>
              </div>
            </div>

            <div class="feature-card" onclick="switchView('tools')">
              <div>
                <div class="card-top">
                  <div class="card-icon-wrap" style="color: #2dd4bf;">🔧</div>
                  <svg class="card-illustration" viewBox="0 0 80 60" fill="none">
                    <rect x="20" y="14" width="55" height="40" rx="7" fill="#0f172a" stroke="#2dd4bf" stroke-width="1.2" opacity="0.9"/>
                    <line x1="20" y1="24" x2="75" y2="24" stroke="#2dd4bf" stroke-width="1" opacity="0.5"/>
                    <path d="M30 36 L36 41 L30 46" stroke="#2dd4bf" stroke-width="2" stroke-linecap="round"/>
                  </svg>
                </div>
                <div class="card-body">
                  <h4>Run Tools</h4>
                  <span class="card-tag">MCP</span>
                  <p>Execute MCP tools and automate your workflow.</p>
                </div>
              </div>
              <div class="card-footer">
                <span style="font-size: 0.72rem; color: var(--text-dim);">Interactive Sandbox</span>
                <div class="arrow-btn">→</div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- VIEW 2: FILES EXPLORER -->
      <div class="view-container" id="view-files">
        <div class="view-card">
          <div class="view-header">
            <h3 class="view-title"><span>📁</span> Workspace File Explorer</h3>
            <button class="nav-btn" onclick="refreshFileTree()"><span>🔄</span> Refresh</button>
          </div>
          <div class="file-explorer">
            <div class="tree-pane" id="fileTreePane">
              <p style="color: var(--text-dim); font-size: 0.8rem;">Loading workspace files...</p>
            </div>
            <div class="code-viewer-pane">
              <div class="code-viewer-header">
                <span id="selectedFileName" style="font-size: 0.85rem; font-weight: 700; color: #a5b4fc;">No file selected</span>
                <div style="display: flex; gap: 0.5rem;">
                  <button class="mini-btn" onclick="askAiAboutFile()">✨ Explain with OmniPlus</button>
                  <button class="mini-btn" onclick="copyCurrentFile()">📋 Copy</button>
                </div>
              </div>
              <div class="code-pre-box" id="fileContentPre">// Click a file on the left to preview contents</div>
            </div>
          </div>
        </div>
      </div>

      <!-- VIEW 3: WEB SEARCH EXPLORER -->
      <div class="view-container" id="view-search">
        <div class="view-card">
          <div class="view-header">
            <h3 class="view-title"><span>🌐</span> Live Web Search</h3>
          </div>
          <div class="search-input-box">
            <input type="text" class="search-bar" id="webSearchInput" placeholder="Search the internet using DuckDuckGo FastMCP..." />
            <button class="send-pill-btn" onclick="executeWebSearch()">Search</button>
          </div>
          <div class="search-results-grid" id="searchResultsGrid">
            <p style="color: var(--text-dim); font-size: 0.85rem;">Enter a query above to fetch real-time search results.</p>
          </div>
        </div>
      </div>

      <!-- VIEW 4: GITHUB VIEW -->
      <div class="view-container" id="view-github">
        <div class="view-card">
          <div class="view-header">
            <h3 class="view-title"><span>🐙</span> GitHub Integration</h3>
            <a href="https://github.com/chethangowda-web/OmniPlus" target="_blank" class="nav-btn">Open on GitHub ↗</a>
          </div>
          <p style="color: var(--text-muted); font-size: 0.88rem; line-height: 1.6;">
            OmniPlus connects to GitHub through <b>@modelcontextprotocol/server-github</b>. You can query open issues, inspect PRs, browse commits, and search across repositories.
          </p>
          <div style="background: #090c16; border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem;">
            <h4 style="font-size: 0.92rem; color: #fff; margin-bottom: 0.5rem;">Quick GitHub Actions</h4>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <button class="nav-btn" style="justify-content: flex-start;" onclick="quickPrompt('List the latest commits on the active branch.')">
                📌 List recent commits
              </button>
              <button class="nav-btn" style="justify-content: flex-start;" onclick="quickPrompt('Inspect open issues and pull requests in this repository.')">
                📋 Inspect open issues & PRs
              </button>
              <button class="nav-btn" style="justify-content: flex-start;" onclick="quickPrompt('Perform a code review of the latest changes in OmniPlus.')">
                🔍 Perform AI Code Review
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- VIEW 5: MCP TOOLS PLAYGROUND -->
      <div class="view-container" id="view-tools">
        <div class="view-card">
          <div class="view-header">
            <h3 class="view-title"><span>🔧</span> Loaded MCP Tools Sandbox</h3>
            <button class="nav-btn" onclick="loadDetailedTools()"><span>🔄</span> Refresh Tools</button>
          </div>
          <p style="color: var(--text-dim); font-size: 0.82rem;">Tools loaded via stdio transports and bound to LangChain ReAct Agent.</p>
          <div class="tools-list-grid" id="toolsDetailedGrid">
            <p style="color: var(--text-dim);">Loading MCP tools metadata...</p>
          </div>
        </div>
      </div>

      <!-- VIEW 6: SETTINGS -->
      <div class="view-container" id="view-settings">
        <div class="view-card">
          <div class="view-header">
            <h3 class="view-title"><span>⚙️</span> AI Provider & System Settings</h3>
          </div>
          <div class="settings-form">
            <!-- Provider Selection -->
            <div class="form-group">
              <label class="form-label" style="font-weight: 700; color: #fff;">Choose Active AI Provider</label>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; margin-top: 0.4rem;">
                <div id="providerOptionGroq" class="provider-select-box active" onclick="setUiProvider('groq')" style="cursor: pointer; padding: 1rem; border: 1.5px solid #6366f1; border-radius: 12px; background: rgba(99, 102, 241, 0.12); transition: all 0.2s ease;">
                  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.35rem;">
                    <span style="font-weight: 700; color: #fff; font-size: 0.95rem;">⚡ Groq Cloud (Recommended)</span>
                    <span class="badge-pill" style="background: rgba(34, 197, 94, 0.2); color: #4ade80;">14.4k Req/Day</span>
                  </div>
                  <p style="color: var(--text-dim); font-size: 0.77rem; margin: 0; line-height: 1.45;">
                    Ultra-fast LPU inference, 30 RPM, no daily lockouts. Recommended for uninterrupted pairs.
                  </p>
                </div>
                <div id="providerOptionGemini" class="provider-select-box" onclick="setUiProvider('gemini')" style="cursor: pointer; padding: 1rem; border: 1px solid var(--border); border-radius: 12px; background: rgba(255, 255, 255, 0.02); transition: all 0.2s ease;">
                  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.35rem;">
                    <span style="font-weight: 700; color: #fff; font-size: 0.95rem;">✨ Google Gemini</span>
                    <span class="badge-pill" style="background: rgba(239, 68, 68, 0.2); color: #f87171;">20 Req/Day</span>
                  </div>
                  <p style="color: var(--text-dim); font-size: 0.77rem; margin: 0; line-height: 1.45;">
                    Standard Google AI Studio models (Free tier capped at 20 requests per day).
                  </p>
                </div>
              </div>
            </div>

            <!-- Groq Settings Panel -->
            <div id="groqSettingsBlock" style="margin-top: 0.5rem;">
              <div class="form-group">
                <label class="form-label">Groq Model</label>
                <select class="form-input" id="settingGroqModelSelect">
                  <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile (Best Reasoning, 128k context — Recommended)</option>
                  <option value="llama-3.1-8b-instant">llama-3.1-8b-instant (Fastest ~800 tokens/sec)</option>
                  <option value="mixtral-8x7b-32768">mixtral-8x7b-32768 (32k context MoE)</option>
                  <option value="gemma2-9b-it">gemma2-9b-it (Google Gemma 2 on Groq)</option>
                </select>
              </div>

              <div class="form-group">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                  <label class="form-label" style="margin: 0;">Groq API Key</label>
                  <span id="groqKeyStatusBadge" style="font-size: 0.73rem; color: #f87171; font-weight: 600;">Not configured</span>
                </div>
                <input type="password" class="form-input" id="settingGroqApiKeyInput" placeholder="Enter your Groq key (gsk_...)" />
                <div style="display: flex; justify-content: space-between; margin-top: 0.4rem; font-size: 0.74rem;">
                  <span style="color: var(--text-dim);">Keys are securely saved in your local git-ignored .env file.</span>
                  <a href="https://console.groq.com/keys" target="_blank" style="color: #818cf8; text-decoration: underline; font-weight: 600;">👉 Get Free Groq Key (Takes 10s)</a>
                </div>
              </div>
            </div>

            <!-- Gemini Settings Panel -->
            <div id="geminiSettingsBlock" style="margin-top: 0.5rem; display: none;">
              <div class="form-group">
                <label class="form-label">Gemini Model</label>
                <select class="form-input" id="settingGeminiModelSelect">
                  <option value="gemini-3.5-flash">gemini-3.5-flash (Fast & Fresh Quota)</option>
                  <option value="gemini-flash-latest">gemini-flash-latest</option>
                  <option value="gemini-3.5-flash-lite">gemini-3.5-flash-lite (High RPM)</option>
                  <option value="gemini-3.1-flash-lite">gemini-3.1-flash-lite</option>
                  <option value="gemma-4-31b-it">gemma-4-31b-it</option>
                </select>
              </div>

              <div class="form-group">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                  <label class="form-label" style="margin: 0;">Google Gemini API Key</label>
                  <span id="geminiKeyStatusBadge" style="font-size: 0.73rem; color: #4ade80; font-weight: 600;">Configured</span>
                </div>
                <input type="password" class="form-input" id="settingGeminiApiKeyInput" placeholder="Update Gemini API Key..." />
                <div style="display: flex; justify-content: space-between; margin-top: 0.4rem; font-size: 0.74rem;">
                  <span style="color: var(--text-dim);">Google AI Studio Key</span>
                  <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color: #818cf8; text-decoration: underline;">Get Gemini Key</a>
                </div>
              </div>
            </div>

            <div style="display: flex; gap: 0.8rem; margin-top: 0.8rem;">
              <button class="send-pill-btn" onclick="saveSystemSettings()" style="padding: 0.65rem 1.6rem; font-size: 0.88rem;">
                💾 Save Configuration
              </button>
            </div>

            <div style="margin-top: 1.25rem; padding: 1.1rem; background: #090c16; border: 1px solid var(--border); border-radius: 12px;">
              <h5 style="color: #fff; font-size: 0.86rem; margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.4rem;">
                🛡️ Automated Resilience & Zero-Downtime Failover
              </h5>
              <p style="color: var(--text-muted); font-size: 0.78rem; line-height: 1.55; margin: 0;">
                If your active model runs into rate limits or quota exhaustion, OmniPlus automatically cascades through the fallback models and cross-fails over between Groq and Gemini to ensure continuous assistant availability!
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- CONVERSATION DRAWER (STREAMING) -->
      <section class="chat-drawer" id="chatDrawer">
        <div class="drawer-top">
          <div class="drawer-title">
            <span style="color: #818cf8;">💬</span> Active OmniPlus Conversation
          </div>
          <div class="drawer-controls">
            <button class="mini-btn" onclick="exportConversation()">📥 Export .md</button>
            <button class="close-btn" onclick="toggleDrawer(false)" title="Minimize conversation">✕</button>
          </div>
        </div>
        <div class="msg-group" id="msgGroup"></div>
      </section>

      <!-- BOTTOM FLOATING CHAT INPUT BAR WITH SPEECH MIC -->
      <div class="chat-input-bar">
        <span class="chat-sparkle">✨</span>
        <input type="text" id="mainInput" placeholder="Ask OmniPlus or prompt a tool action... (Press Enter)" autofocus />
        <button class="mic-btn" id="micBtn" onclick="toggleSpeechRecognition()" title="Voice input (Speech to Text)">🎙️</button>
        <button class="send-pill-btn" id="sendBtn" onclick="submitMessage()">
          <span>Send</span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>

    </main>

    <!-- RIGHT SIDEBAR -->
    <aside class="sidebar-right">

      <!-- QUICK ACTIONS PANEL -->
      <div class="panel-box">
        <div class="panel-header">
          <h4 class="panel-title">
            <span style="color: #818cf8;">⚡</span> Quick Actions
          </h4>
        </div>
        <p class="panel-desc">Jump into what you need</p>

        <div class="action-row" onclick="switchView('search')">
          <div class="action-left">
            <div class="action-icon" style="color: #38bdf8;">🌐</div>
            <div class="action-meta">
              <h5>Search the Web</h5>
              <p>Find latest information</p>
            </div>
          </div>
          <span class="chevron-right">›</span>
        </div>

        <div class="action-row" onclick="switchView('files')">
          <div class="action-left">
            <div class="action-icon" style="color: #f59e0b;">📁</div>
            <div class="action-meta">
              <h5>Browse Files</h5>
              <p>Check project files</p>
            </div>
          </div>
          <span class="chevron-right">›</span>
        </div>

        <div class="action-row" onclick="switchView('github')">
          <div class="action-left">
            <div class="action-icon" style="color: #c084fc;">🐙</div>
            <div class="action-meta">
              <h5>Use GitHub</h5>
              <p>Explore repositories</p>
            </div>
          </div>
          <span class="chevron-right">›</span>
        </div>

        <div class="action-row" onclick="switchView('tools')">
          <div class="action-left">
            <div class="action-icon" style="color: #2dd4bf;">🔧</div>
            <div class="action-meta">
              <h5>Run MCP Tools</h5>
              <p>Execute powerful tools</p>
            </div>
          </div>
          <span class="chevron-right">›</span>
        </div>
      </div>

      <!-- RECENT ACTIVITY PANEL -->
      <div class="panel-box">
        <div class="panel-header">
          <h4 class="panel-title">
            <span style="color: #38bdf8;">🕒</span> Recent Activity
          </h4>
          <span class="panel-link" onclick="quickPrompt('Summarize recent interactions and tool executions.')" style="color: #6366f1; font-size: 0.72rem; cursor: pointer;">View all</span>
        </div>

        <div class="activity-list" id="activityList">
          <div class="activity-item">
            <div class="activity-icon icon-blue">🌐</div>
            <div class="activity-text">
              <h6>Searched: Python MCP</h6>
              <span>2 minutes ago</span>
            </div>
          </div>

          <div class="activity-item">
            <div class="activity-icon icon-amber">📁</div>
            <div class="activity-text">
              <h6>Read file: main.py</h6>
              <span>12 minutes ago</span>
            </div>
          </div>

          <div class="activity-item">
            <div class="activity-icon icon-purple">✨</div>
            <div class="activity-text">
              <h6>Used Gemini for analysis</h6>
              <span>28 minutes ago</span>
            </div>
          </div>

          <div class="activity-item">
            <div class="activity-icon icon-green">🔧</div>
            <div class="activity-text">
              <h6>Executed MCP tool</h6>
              <span>1 hour ago</span>
            </div>
          </div>
        </div>
      </div>

      <!-- INSPIRATION BANNER (RIGHT BOTTOM) -->
      <div class="promo-mountain-card" onclick="quickPrompt('What are the best practices for building MCP agents?')">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <h4>Better tools.<br>Bigger dreams.</h4>
          </div>
          <div class="arrow-btn" style="background: rgba(99, 102, 241, 0.25);">→</div>
        </div>
        <svg viewBox="0 0 200 65" fill="none">
          <polygon points="10,65 60,18 115,65" fill="#1e1b4b" opacity="0.6"/>
          <polygon points="75,65 130,8 185,65" fill="url(#gradM2)"/>
          <circle cx="130" cy="8" r="3" fill="#ec4899"/>
          <line x1="130" y1="8" x2="130" y2="16" stroke="#ec4899" stroke-width="1.5"/>
          <polygon points="130,8 138,10 130,14" fill="#ec4899"/>
          <defs>
            <linearGradient id="gradM2" x1="130" y1="8" x2="130" y2="65" gradientUnits="userSpaceOnUse">
              <stop stop-color="#6366f1"/>
              <stop offset="1" stop-color="#0c1228"/>
            </linearGradient>
          </defs>
        </svg>
      </div>

    </aside>

  </div>

  <script>
    const mainInput = document.getElementById('mainInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatDrawer = document.getElementById('chatDrawer');
    const msgGroup = document.getElementById('msgGroup');
    const activityList = document.getElementById('activityList');
    const micBtn = document.getElementById('micBtn');

    let chatHistoryLog = [];
    let currentSelectedFilePath = '';

    // Greeting calculation
    (function setGreeting() {
      const hour = new Date().getHours();
      const el = document.getElementById('timeGreeting');
      if (hour >= 5 && hour < 12) el.textContent = 'morning';
      else if (hour >= 12 && hour < 17) el.textContent = 'afternoon';
      else el.textContent = 'evening';
    })();

    // View Switching
    function switchView(viewName) {
      document.querySelectorAll('.view-container').forEach(el => el.classList.remove('active-view'));
      document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

      const targetView = document.getElementById(`view-${viewName}`);
      const targetNav = document.getElementById(`nav-${viewName}`);

      if (targetView) targetView.classList.add('active-view');
      if (targetNav) targetNav.classList.add('active');

      if (viewName === 'files') refreshFileTree();
      else if (viewName === 'tools') loadDetailedTools();
      else if (viewName === 'settings') loadSettingsInfo();
    }

    mainInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') submitMessage();
    });

    document.getElementById('webSearchInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') executeWebSearch();
    });

    function quickPrompt(text) {
      switchView('home');
      mainInput.value = text;
      submitMessage();
    }

    function toggleDrawer(show) {
      if (show) chatDrawer.classList.add('open');
      else chatDrawer.classList.remove('open');
    }

    // REAL-TIME TOKEN STREAMING (SSE)
    async function submitMessage() {
      const text = mainInput.value.trim();
      if (!text) return;

      mainInput.value = '';
      toggleDrawer(true);

      // Append user message
      appendMessage('user', text);
      chatHistoryLog.push({ role: 'user', content: text });

      sendBtn.disabled = true;
      sendBtn.innerHTML = '<span class="spinner"></span> Streaming...';

      // Create assistant container
      const assistantMsg = appendMessage('assistant', '<div class="tool-status-container"></div><div class="stream-text"></div>');
      const streamTextEl = assistantMsg.querySelector('.stream-text');
      const toolStatusEl = assistantMsg.querySelector('.tool-status-container');

      logRecentActivity(text);

      let accumulatedText = '';

      try {
        const response = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text })
        });

        if (!response.ok) {
          throw new Error(`HTTP Error: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\\n');
          buffer = lines.pop();

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const jsonStr = line.slice(6).trim();
              if (!jsonStr) continue;
              try {
                const data = JSON.parse(jsonStr);
                if (data.type === 'token') {
                  accumulatedText += data.text;
                  streamTextEl.innerHTML = marked.parse(accumulatedText);
                  enhanceCodeBlocks(streamTextEl);
                } else if (data.type === 'tool_start') {
                  toolStatusEl.innerHTML = `<span class="tool-badge-pill">🔧 Executing: <b>${data.tool}</b>...</span>`;
                } else if (data.type === 'tool_end') {
                  toolStatusEl.innerHTML = `<span class="tool-badge-pill" style="border-color: rgba(16,185,129,0.4); color: #34d399;">✓ Tool complete: <b>${data.tool}</b></span>`;
                } else if (data.type === 'error') {
                  toolStatusEl.innerHTML = '';
                  let msg = data.message;
                  let actionHtml = '';
                  if (msg.includes('429') || msg.includes('quota') || msg.includes('RESOURCE_EXHAUSTED') || msg.includes('Groq API Key Required') || msg.includes('Groq')) {
                    actionHtml = `
                      <div style="margin-top: 0.8rem;">
                        <button class="send-pill-btn" onclick="switchView('settings')" style="padding: 0.45rem 1.1rem; font-size: 0.8rem;">
                          ⚙️ Open Settings to Add Groq Key
                        </button>
                      </div>
                    `;
                  }
                  streamTextEl.innerHTML = `<div style="padding: 0.5rem 0; color: #fbbf24;">⚠️ ${msg}${actionHtml}</div>`;
                }
              } catch (e) {
                // Ignore parse errors on chunk boundary
              }
            }
          }
          chatDrawer.scrollTop = chatDrawer.scrollHeight;
        }

        chatHistoryLog.push({ role: 'assistant', content: accumulatedText });

      } catch (err) {
        streamTextEl.innerHTML = `<p style="color: #f87171;">⚠️ <b>Connection error:</b> ${err.message}</p>`;
      } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = `<span>Send</span> <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>`;
        chatDrawer.scrollTop = chatDrawer.scrollHeight;
        mainInput.focus();
      }
    }

    function appendMessage(role, htmlContent) {
      const msg = document.createElement('div');
      msg.className = `msg ${role}`;
      msg.innerHTML = `
        <div class="msg-avatar">${role === 'user' ? '👤' : '🤖'}</div>
        <div class="msg-bubble">${htmlContent}</div>
      `;
      msgGroup.appendChild(msg);
      chatDrawer.scrollTop = chatDrawer.scrollHeight;
      return msg;
    }

    // CODE BLOCK SYNTAX HIGHLIGHTING & COPY BUTTON
    function enhanceCodeBlocks(container) {
      container.querySelectorAll('pre code').forEach((block) => {
        if (!block.dataset.highlighted) {
          hljs.highlightElement(block);
          block.dataset.highlighted = 'true';

          const pre = block.parentElement;
          if (!pre.parentElement.classList.contains('code-container')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'code-container';
            pre.parentNode.insertBefore(wrapper, pre);
            wrapper.appendChild(pre);

            const copyBtn = document.createElement('button');
            copyBtn.className = 'code-copy-btn';
            copyBtn.textContent = 'Copy';
            copyBtn.onclick = () => {
              navigator.clipboard.writeText(block.innerText);
              copyBtn.textContent = 'Copied!';
              setTimeout(() => copyBtn.textContent = 'Copy', 1800);
            };
            wrapper.appendChild(copyBtn);
          }
        }
      });
    }

    // WEB SPEECH RECOGNITION (VOICE INPUT)
    let recognition = null;
    let isListening = false;
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        mainInput.value = transcript;
        stopSpeech();
      };
      recognition.onerror = () => stopSpeech();
      recognition.onend = () => stopSpeech();
    }

    function toggleSpeechRecognition() {
      if (!recognition) {
        alert('Speech recognition is not supported in this browser. Try Chrome or Edge.');
        return;
      }
      if (isListening) stopSpeech();
      else startSpeech();
    }

    function startSpeech() {
      isListening = true;
      micBtn.classList.add('listening');
      recognition.start();
    }

    function stopSpeech() {
      isListening = false;
      micBtn.classList.remove('listening');
      try { recognition.stop(); } catch (e) {}
    }

    // EXPORT CONVERSATION
    function exportConversation() {
      if (!chatHistoryLog.length) {
        alert('No conversation to export yet.');
        return;
      }
      let md = `# OmniPlus Conversation Export\\n*Exported on ${new Date().toLocaleString()}*\\n\\n---\\n\\n`;
      chatHistoryLog.forEach(m => {
        md += `### ${m.role === 'user' ? '👤 User' : '🤖 OmniPlus'}:\\n\\n${m.content}\\n\\n---\\n\\n`;
      });
      const blob = new Blob([md], { type: 'text/markdown' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `omniplus-chat-${Date.now()}.md`;
      a.click();
    }

    // RECENT ACTIVITY LOGGER
    function logRecentActivity(query) {
      let icon = '✨';
      let iconClass = 'icon-purple';
      let cleanQuery = query.length > 25 ? query.substring(0, 25) + '...' : query;

      if (query.toLowerCase().includes('search') || query.toLowerCase().includes('web')) {
        icon = '🌐';
        iconClass = 'icon-blue';
      } else if (query.toLowerCase().includes('file') || query.toLowerCase().includes('dir')) {
        icon = '📁';
        iconClass = 'icon-amber';
      } else if (query.toLowerCase().includes('tool')) {
        icon = '🔧';
        iconClass = 'icon-green';
      }

      const item = document.createElement('div');
      item.className = 'activity-item';
      item.innerHTML = `
        <div class="activity-icon ${iconClass}">${icon}</div>
        <div class="activity-text">
          <h6>${cleanQuery}</h6>
          <span>Just now</span>
        </div>
      `;
      activityList.insertBefore(item, activityList.firstChild);
      if (activityList.children.length > 5) {
        activityList.removeChild(activityList.lastChild);
      }
    }

    // FILE TREE EXPLORER
    async function refreshFileTree() {
      const pane = document.getElementById('fileTreePane');
      pane.innerHTML = '<p style="color: var(--text-dim); font-size: 0.8rem;">Loading tree...</p>';
      try {
        const res = await fetch('/api/files/tree');
        const data = await res.json();
        pane.innerHTML = renderTreeNodes(data.tree);
      } catch (e) {
        pane.innerHTML = `<p style="color: #f87171;">Failed to load files: ${e.message}</p>`;
      }
    }

    function renderTreeNodes(nodes, level = 0) {
      let html = '';
      nodes.forEach(node => {
        const indent = level * 14;
        if (node.type === 'dir') {
          html += `
            <div class="tree-item" style="padding-left: ${indent}px; font-weight: 700; color: #cbd5e1;">
              <span>📁</span> ${node.name}
            </div>
          `;
          if (node.children && node.children.length) {
            html += renderTreeNodes(node.children, level + 1);
          }
        } else {
          html += `
            <div class="tree-item" style="padding-left: ${indent}px;" onclick="loadFileContent('${node.path}', this)">
              <span>📄</span> ${node.name}
            </div>
          `;
        }
      });
      return html;
    }

    async function loadFileContent(filePath, el) {
      document.querySelectorAll('.tree-item').forEach(i => i.classList.remove('selected'));
      if (el) el.classList.add('selected');

      currentSelectedFilePath = filePath;
      document.getElementById('selectedFileName').textContent = filePath;
      const pre = document.getElementById('fileContentPre');
      pre.textContent = 'Loading...';

      try {
        const res = await fetch(`/api/files/content?path=${encodeURIComponent(filePath)}`);
        const data = await res.json();
        pre.textContent = data.content;
      } catch (e) {
        pre.textContent = `Error reading file: ${e.message}`;
      }
    }

    function askAiAboutFile() {
      if (!currentSelectedFilePath) {
        alert('Please select a file first.');
        return;
      }
      quickPrompt(`Analyze and explain the contents of file: ${currentSelectedFilePath}`);
    }

    function copyCurrentFile() {
      const text = document.getElementById('fileContentPre').textContent;
      navigator.clipboard.writeText(text);
      alert('File content copied to clipboard!');
    }

    // LIVE WEB SEARCH TAB
    async function executeWebSearch() {
      const q = document.getElementById('webSearchInput').value.trim();
      if (!q) return;

      const grid = document.getElementById('searchResultsGrid');
      grid.innerHTML = '<p style="color: var(--text-dim);">Searching DuckDuckGo via MCP...</p>';

      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        if (!data.results || !data.results.length) {
          grid.innerHTML = '<p style="color: var(--text-dim);">No results found.</p>';
          return;
        }
        grid.innerHTML = data.results.map(r => `
          <div class="search-card">
            <h4>${r.title}</h4>
            <a href="${r.href}" target="_blank">${r.href}</a>
            <p>${r.body}</p>
            <button class="mini-btn" style="margin-top: 0.6rem;" onclick="quickPrompt('Summarize information from: ${r.title} (${r.href})')">
              ✨ Summarize with Gemini
            </button>
          </div>
        `).join('');
      } catch (e) {
        grid.innerHTML = `<p style="color: #f87171;">Search error: ${e.message}</p>`;
      }
    }

    // TOOLS DETAILS TAB
    async function loadDetailedTools() {
      const grid = document.getElementById('toolsDetailedGrid');
      grid.innerHTML = '<p style="color: var(--text-dim);">Inspecting MCP servers...</p>';

      try {
        const res = await fetch('/api/tools/detailed');
        const data = await res.json();
        if (!data.tools || !data.tools.length) {
          grid.innerHTML = '<p style="color: var(--text-dim);">No tools loaded.</p>';
          return;
        }
        grid.innerHTML = data.tools.map(t => `
          <div class="tool-box-card">
            <div>
              <h4>${t.name}</h4>
              <p>${t.description}</p>
            </div>
            <button class="send-pill-btn" style="padding: 0.35rem 0.8rem; font-size: 0.75rem; align-self: flex-start;" onclick="quickPrompt('Demonstrate the MCP tool: ${t.name}')">
              Test Tool ⚡
            </button>
          </div>
        `).join('');
      } catch (e) {
        grid.innerHTML = `<p style="color: #f87171;">Error: ${e.message}</p>`;
      }
    }

    // SETTINGS MANAGER
    let selectedProvider = 'groq';

    function setUiProvider(p) {
      selectedProvider = p;
      const groqBox = document.getElementById('providerOptionGroq');
      const geminiBox = document.getElementById('providerOptionGemini');
      const groqBlock = document.getElementById('groqSettingsBlock');
      const geminiBlock = document.getElementById('geminiSettingsBlock');

      if (!groqBox || !geminiBox || !groqBlock || !geminiBlock) return;

      if (p === 'groq') {
        groqBox.style.borderColor = '#6366f1';
        groqBox.style.background = 'rgba(99, 102, 241, 0.12)';
        geminiBox.style.borderColor = 'var(--border)';
        geminiBox.style.background = 'rgba(255, 255, 255, 0.02)';
        groqBlock.style.display = 'block';
        geminiBlock.style.display = 'none';
      } else {
        geminiBox.style.borderColor = '#6366f1';
        geminiBox.style.background = 'rgba(99, 102, 241, 0.12)';
        groqBox.style.borderColor = 'var(--border)';
        groqBox.style.background = 'rgba(255, 255, 255, 0.02)';
        groqBlock.style.display = 'none';
        geminiBlock.style.display = 'block';
      }
    }

    async function loadSettingsInfo() {
      try {
        const res = await fetch('/api/config');
        const data = await res.json();

        selectedProvider = data.provider || 'groq';
        setUiProvider(selectedProvider);

        if (data.groq_model && document.getElementById('settingGroqModelSelect')) {
          document.getElementById('settingGroqModelSelect').value = data.groq_model;
        }
        if (data.gemini_model && document.getElementById('settingGeminiModelSelect')) {
          document.getElementById('settingGeminiModelSelect').value = data.gemini_model;
        }

        const groqBadge = document.getElementById('groqKeyStatusBadge');
        if (groqBadge) {
          if (data.has_groq) {
            groqBadge.textContent = `Configured (${data.groq_key_masked})`;
            groqBadge.style.color = '#4ade80';
          } else {
            groqBadge.textContent = '❌ Key Missing (Add below)';
            groqBadge.style.color = '#f87171';
          }
        }

        const geminiBadge = document.getElementById('geminiKeyStatusBadge');
        if (geminiBadge) {
          if (data.has_gemini) {
            geminiBadge.textContent = `Configured (${data.gemini_key_masked})`;
            geminiBadge.style.color = '#4ade80';
          } else {
            geminiBadge.textContent = 'Not configured';
            geminiBadge.style.color = 'var(--text-dim)';
          }
        }

        const provLabel = selectedProvider === 'groq' ? '⚡ Groq' : '✨ Gemini';
        const activeModel = selectedProvider === 'groq' ? (data.groq_model || 'llama-3.3-70b-versatile') : (data.gemini_model || 'gemini-3.5-flash');
        const navStatus = document.getElementById('navModelStatus');
        if (navStatus) {
          navStatus.textContent = `Ready • ${provLabel} (${activeModel})`;
        }
      } catch (e) {
        console.error('Error loading config:', e);
      }
    }

    async function saveSystemSettings() {
      const groqModel = document.getElementById('settingGroqModelSelect')?.value;
      const groqApiKey = document.getElementById('settingGroqApiKeyInput')?.value;
      const geminiModel = document.getElementById('settingGeminiModelSelect')?.value;
      const geminiApiKey = document.getElementById('settingGeminiApiKeyInput')?.value;

      try {
        const res = await fetch('/api/settings/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider: selectedProvider,
            groq_model: groqModel,
            groq_api_key: groqApiKey,
            gemini_model: geminiModel,
            gemini_api_key: geminiApiKey,
          })
        });
        const data = await res.json();
        if (data.status === 'updated') {
          const provLabel = data.provider === 'groq' ? '⚡ Groq' : '✨ Gemini';
          document.getElementById('navModelStatus').textContent = `Ready • ${provLabel} (${data.model})`;
          alert(`✅ Configuration updated successfully!\nActive Provider: ${data.provider.toUpperCase()}\nModel: ${data.model}`);
          loadSettingsInfo();
        } else {
          alert(`Notice: ${JSON.stringify(data)}`);
        }
      } catch (e) {
        alert(`Failed to save settings: ${e.message}`);
      }
    }

    async function clearAllChat() {
      await fetch('/api/clear', { method: 'POST' });
      msgGroup.innerHTML = '';
      chatHistoryLog = [];
      toggleDrawer(false);
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
