"""FastAPI Web Server for OmniPlus AI Assistant — Next-Gen Dashboard UI."""
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
        return {"error": str(e), "model": "gemini-2.5-flash", "enabled_servers": ["filesystem", "websearch"]}


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
  <title>OmniPlus — MCP Assistant</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
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
    .nav-btn.danger {
      color: #f87171;
    }
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
    }
    .center-workspace::-webkit-scrollbar {
      width: 6px;
    }
    .center-workspace::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 4px;
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
    .pill-icon {
      font-size: 1.15rem;
    }
    .pill-text h5 {
      font-size: 0.8rem;
      font-weight: 700;
      color: #fff;
    }
    .pill-text p {
      font-size: 0.68rem;
      color: var(--text-dim);
    }

    /* HERO ARTWORK (COSMIC PLANET + ROBOT) */
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

    /* 4 FEATURE CARDS GRID */
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
      position: relative;
      overflow: hidden;
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
    .card-body h4 {
      font-size: 0.95rem;
      font-weight: 700;
      color: #fff;
      margin-bottom: 0.2rem;
    }
    .card-tag {
      font-size: 0.65rem;
      font-weight: 700;
      color: #818cf8;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
      display: inline-block;
    }
    .card-body p {
      font-size: 0.74rem;
      color: var(--text-muted);
      line-height: 1.45;
    }
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
    .feature-card:hover .arrow-btn {
      background: var(--primary);
      color: #fff;
      transform: translateX(3px);
    }

    /* FLOATING CHAT INPUT BAR */
    .chat-input-bar {
      margin-top: auto;
      background: #0e1428;
      border: 1px solid rgba(99, 102, 241, 0.3);
      border-radius: 30px;
      padding: 0.45rem 0.65rem 0.45rem 1.25rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(99, 102, 241, 0.15);
      position: sticky;
      bottom: 0;
      z-index: 50;
    }
    .chat-sparkle {
      font-size: 1.15rem;
      color: #a855f7;
    }
    .chat-input-bar input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      font-size: 0.92rem;
      color: #fff;
      font-family: inherit;
    }
    .chat-input-bar input::placeholder {
      color: var(--text-dim);
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
    .send-pill-btn:hover {
      opacity: 0.92;
      transform: scale(1.02);
    }
    .send-pill-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    /* RIGHT SIDEBAR */
    .sidebar-right {
      display: flex;
      flex-direction: column;
      gap: 1.1rem;
      height: 100%;
      overflow-y: auto;
    }
    .sidebar-right::-webkit-scrollbar {
      width: 4px;
    }
    .sidebar-right::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 4px;
    }
    .panel-box {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 1.1rem;
    }
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 0.85rem;
    }
    .panel-title {
      font-size: 0.88rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }
    .panel-link {
      font-size: 0.72rem;
      color: #6366f1;
      text-decoration: none;
      font-weight: 600;
      cursor: pointer;
    }
    .panel-desc {
      font-size: 0.72rem;
      color: var(--text-dim);
      margin-top: -0.5rem;
      margin-bottom: 0.75rem;
    }
    .action-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.65rem 0.6rem;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .action-row:hover {
      background: rgba(255, 255, 255, 0.04);
    }
    .action-left {
      display: flex;
      align-items: center;
      gap: 0.65rem;
    }
    .action-icon {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.04);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.95rem;
    }
    .action-meta h5 {
      font-size: 0.8rem;
      font-weight: 700;
      color: #fff;
    }
    .action-meta p {
      font-size: 0.68rem;
      color: var(--text-dim);
    }
    .chevron-right {
      color: var(--text-dim);
      font-size: 0.85rem;
      transition: all 0.2s;
    }
    .action-row:hover .chevron-right {
      color: #fff;
      transform: translateX(2px);
    }

    /* ACTIVITY STREAM */
    .activity-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    .activity-item {
      display: flex;
      align-items: center;
      gap: 0.65rem;
      padding: 0.5rem 0.4rem;
      border-radius: 8px;
    }
    .activity-icon {
      width: 28px;
      height: 28px;
      border-radius: 7px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.85rem;
      flex-shrink: 0;
    }
    .icon-blue { background: rgba(14, 165, 233, 0.15); color: #38bdf8; }
    .icon-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
    .icon-purple { background: rgba(168, 85, 247, 0.15); color: #c084fc; }
    .icon-green { background: rgba(16, 185, 129, 0.15); color: #34d399; }
    .activity-text h6 {
      font-size: 0.77rem;
      font-weight: 600;
      color: #e2e8f0;
    }
    .activity-text span {
      font-size: 0.67rem;
      color: var(--text-dim);
    }

    /* PROMO MOUNTAIN RIGHT */
    .promo-mountain-card {
      background: linear-gradient(135deg, #131433 0%, #0c1228 100%);
      border: 1px solid rgba(99, 102, 241, 0.2);
      border-radius: 16px;
      padding: 1.1rem;
      position: relative;
      overflow: hidden;
      margin-top: auto;
    }
    .promo-mountain-card h4 {
      font-size: 0.88rem;
      font-weight: 700;
      color: #fff;
      margin-bottom: 0.15rem;
    }
    .promo-mountain-card p {
      font-size: 0.72rem;
      color: var(--text-muted);
    }
    .promo-mountain-card svg {
      width: 100%;
      height: 70px;
      margin-top: 0.5rem;
    }

    /* CONVERSATION OVERLAY DRAWER */
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
    .chat-drawer.open {
      display: flex;
    }
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
    .close-btn {
      background: transparent;
      border: none;
      color: var(--text-dim);
      font-size: 1.1rem;
      cursor: pointer;
    }
    .close-btn:hover { color: #fff; }

    /* MESSAGE BUBBLE STYLING */
    .msg-group {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .msg {
      display: flex;
      gap: 0.75rem;
      max-width: 88%;
      animation: fadeIn 0.2s ease-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .msg.user {
      align-self: flex-end;
      flex-direction: row-reverse;
    }
    .msg.assistant {
      align-self: flex-start;
    }
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
    .msg.user .msg-avatar {
      background: #4338ca;
    }
    .msg.assistant .msg-avatar {
      background: linear-gradient(135deg, #0ea5e9, #6366f1);
      box-shadow: 0 0 15px rgba(14, 165, 233, 0.35);
    }
    .msg-bubble {
      padding: 0.85rem 1.15rem;
      border-radius: 16px;
      font-size: 0.9rem;
      line-height: 1.55;
    }
    .msg.user .msg-bubble {
      background: #1e1b4b;
      border: 1px solid rgba(99, 102, 241, 0.3);
      color: #e0e7ff;
      border-top-right-radius: 4px;
    }
    .msg.assistant .msg-bubble {
      background: #11172a;
      border: 1px solid var(--border);
      color: var(--text);
      border-top-left-radius: 4px;
    }
    .msg-bubble pre {
      background: #090c16;
      border: 1px solid rgba(255, 255, 255, 0.08);
      padding: 0.75rem;
      border-radius: 8px;
      overflow-x: auto;
      margin: 0.5rem 0;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.82rem;
    }
    .msg-bubble code {
      background: rgba(255, 255, 255, 0.1);
      padding: 0.15rem 0.3rem;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.82rem;
    }
    .msg-bubble pre code { background: none; padding: 0; }
    .msg-bubble p:not(:last-child) { margin-bottom: 0.5rem; }

    .spinner {
      display: inline-block;
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-radius: 50%;
      border-top-color: #fff;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>

  <!-- TOP HEADER -->
  <header class="top-nav">
    <div class="brand">
      <div class="brand-logo">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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
        <span>Ready</span>
      </div>
      <button class="nav-btn" onclick="quickPrompt('Inspect and list files in this project workspace.')">
        <span>📁</span> Files
      </button>
      <button class="nav-btn" onclick="quickPrompt('Search the web for the latest updates on Model Context Protocol.')">
        <span>🌐</span> Search
      </button>
      <button class="nav-btn" onclick="quickPrompt('Check GitHub integration status and loaded tools.')">
        <span>🐙</span> GitHub
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
        <a class="nav-item active" href="#" onclick="selectNav(this, 'home')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
          <span>Home</span>
        </a>
        <a class="nav-item" href="#" onclick="selectNav(this, 'files')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
          <span>Files</span>
        </a>
        <a class="nav-item" href="#" onclick="selectNav(this, 'search')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          <span>Search</span>
        </a>
        <a class="nav-item" href="#" onclick="selectNav(this, 'github')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>
          <span>GitHub</span>
        </a>
        <a class="nav-item" href="#" onclick="selectNav(this, 'tools')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>
          <span>Tools</span>
        </a>
        <a class="nav-item" href="#" onclick="selectNav(this, 'settings')">
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
        <div class="user-footer" onclick="quickPrompt('Display OmniPlus configuration and model details.')">
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

    <!-- CENTER MAIN WORKSPACE -->
    <main class="center-workspace">

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

        <!-- 3D COSMIC PLANET + ROBOT GRAPHIC -->
        <div class="hero-art">
          <div class="planet-glow"></div>
          <svg class="robot-cliff" viewBox="0 0 200 160" fill="none">
            <!-- Mountain silhouette -->
            <path d="M0 160 L50 115 L110 90 L160 110 L200 160 Z" fill="#0c1228" opacity="0.95"/>
            <path d="M70 160 L120 85 L180 120 L200 160 Z" fill="#141935" opacity="0.85"/>
            <!-- Cliff ledge -->
            <path d="M95 105 L155 100 L185 160 L75 160 Z" fill="#080b18"/>
            <!-- Sitting Robot with Laptop -->
            <g transform="translate(125, 60)">
              <!-- Robot Head -->
              <rect x="10" y="2" width="22" height="18" rx="6" fill="#e2e8f0"/>
              <!-- Screen eyes -->
              <rect x="13" y="6" width="16" height="9" rx="3" fill="#0f172a"/>
              <ellipse cx="17" cy="10" rx="1.8" ry="2.2" fill="#38bdf8"/>
              <ellipse cx="25" cy="10" rx="1.8" ry="2.2" fill="#38bdf8"/>
              <!-- Antenna -->
              <line x1="21" y1="2" x2="21" y2="-4" stroke="#94a3b8" stroke-width="1.8"/>
              <circle cx="21" cy="-5" r="2" fill="#818cf8"/>
              <!-- Robot Body -->
              <rect x="8" y="22" width="26" height="24" rx="7" fill="#cbd5e1"/>
              <!-- Chest emblem -->
              <circle cx="21" cy="32" r="4.5" fill="#38bdf8" opacity="0.8"/>
              <!-- Sitting legs -->
              <rect x="4" y="42" width="16" height="7" rx="3" fill="#94a3b8"/>
              <rect x="22" y="42" width="16" height="7" rx="3" fill="#94a3b8"/>
              <!-- Laptop -->
              <polygon points="26,38 42,38 40,44 24,44" fill="#64748b"/>
              <polygon points="34,26 44,26 42,38 32,38" fill="#38bdf8" opacity="0.9"/>
              <!-- Glowing keyboard glow -->
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

          <!-- CARD 1: SEARCH WEB -->
          <div class="feature-card" onclick="quickPrompt('Search the web for Model Context Protocol news.')">
            <div>
              <div class="card-top">
                <div class="card-icon-wrap" style="color: #38bdf8;">🔍</div>
                <svg class="card-illustration" viewBox="0 0 80 60" fill="none">
                  <circle cx="45" cy="30" r="24" stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="3 3" opacity="0.7"/>
                  <ellipse cx="45" cy="30" rx="24" ry="10" stroke="#38bdf8" stroke-width="1.2" opacity="0.8"/>
                  <ellipse cx="45" cy="30" rx="10" ry="24" stroke="#38bdf8" stroke-width="1.2" opacity="0.8"/>
                  <circle cx="58" cy="22" r="3" fill="#0ea5e9"/>
                  <circle cx="35" cy="36" r="2" fill="#38bdf8"/>
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

          <!-- CARD 2: INSPECT FILES -->
          <div class="feature-card" onclick="quickPrompt('List and summarize files in the current directory.')">
            <div>
              <div class="card-top">
                <div class="card-icon-wrap" style="color: #34d399;">📁</div>
                <svg class="card-illustration" viewBox="0 0 80 60" fill="none">
                  <path d="M20 22 C20 18, 22 16, 26 16 L38 16 L44 22 L68 22 C72 22, 74 24, 74 28 L74 46 C74 50, 72 52, 68 52 L26 52 C22 52, 20 50, 20 46 Z" fill="#065f46" opacity="0.6"/>
                  <path d="M12 28 C12 24, 14 22, 18 22 L30 22 L36 28 L60 28 C64 28, 66 30, 66 34 L66 52 C66 56, 64 58, 60 58 L18 58 C14 58, 12 56, 12 52 Z" fill="#047857" opacity="0.8"/>
                  <path d="M8 34 C8 30, 10 28, 14 28 L26 28 L32 34 L54 34 C58 34, 60 36, 60 40 L60 56 C60 60, 58 62, 54 62 L14 62 C10 62, 8 60, 8 56 Z" fill="url(#gradFolder)"/>
                  <defs>
                    <linearGradient id="gradFolder" x1="8" y1="28" x2="60" y2="62" gradientUnits="userSpaceOnUse">
                      <stop stop-color="#10b981"/>
                      <stop offset="1" stop-color="#047857"/>
                    </linearGradient>
                  </defs>
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

          <!-- CARD 3: ASK GEMINI -->
          <div class="feature-card" onclick="quickPrompt('How can I use OmniPlus to optimize my software development?')">
            <div>
              <div class="card-top">
                <div class="card-icon-wrap" style="color: #c084fc;">✨</div>
                <svg class="card-illustration" viewBox="0 0 80 60" fill="none">
                  <!-- Sparkling stars -->
                  <path d="M50 10 L53 22 L65 25 L53 28 L50 40 L47 28 L35 25 L47 22 Z" fill="#c084fc"/>
                  <path d="M26 28 L28 35 L35 37 L28 39 L26 46 L24 39 L17 37 L24 35 Z" fill="#a855f7" opacity="0.75"/>
                  <circle cx="62" cy="44" r="3" fill="#e879f9"/>
                  <circle cx="36" cy="16" r="2" fill="#d8b4fe"/>
                </svg>
              </div>
              <div class="card-body">
                <h4>Ask Gemini</h4>
                <span class="card-tag">MCP</span>
                <p>Get intelligent responses using Google Gemini and MCP tools.</p>
              </div>
            </div>
            <div class="card-footer">
              <span style="font-size: 0.72rem; color: var(--text-dim);">gemini-2.5-flash</span>
              <div class="arrow-btn">→</div>
            </div>
          </div>

          <!-- CARD 4: RUN TOOLS -->
          <div class="feature-card" onclick="quickPrompt('List all active MCP tools and show their schema.')">
            <div>
              <div class="card-top">
                <div class="card-icon-wrap" style="color: #2dd4bf;">🔧</div>
                <svg class="card-illustration" viewBox="0 0 80 60" fill="none">
                  <!-- Code terminal window -->
                  <rect x="20" y="14" width="55" height="40" rx="7" fill="#0f172a" stroke="#2dd4bf" stroke-width="1.2" opacity="0.9"/>
                  <line x1="20" y1="24" x2="75" y2="24" stroke="#2dd4bf" stroke-width="1" opacity="0.5"/>
                  <circle cx="26" cy="19" r="1.5" fill="#f43f5e"/>
                  <circle cx="31" cy="19" r="1.5" fill="#facc15"/>
                  <circle cx="36" cy="19" r="1.5" fill="#10b981"/>
                  <path d="M30 36 L36 41 L30 46" stroke="#2dd4bf" stroke-width="2" stroke-linecap="round"/>
                  <line x1="42" y1="46" x2="52" y2="46" stroke="#2dd4bf" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </div>
              <div class="card-body">
                <h4>Run Tools</h4>
                <span class="card-tag">MCP</span>
                <p>Execute MCP tools and automate your workflow.</p>
              </div>
            </div>
            <div class="card-footer">
              <span style="font-size: 0.72rem; color: var(--text-dim);">Automated ReAct</span>
              <div class="arrow-btn">→</div>
            </div>
          </div>

        </div>
      </section>

      <!-- CONVERSATION DRAWER (APPEARS ON QUERY) -->
      <section class="chat-drawer" id="chatDrawer">
        <div class="drawer-top">
          <div class="drawer-title">
            <span style="color: #818cf8;">💬</span> Active OmniPlus Conversation
          </div>
          <button class="close-btn" onclick="toggleDrawer(false)" title="Minimize conversation">✕</button>
        </div>
        <div class="msg-group" id="msgGroup"></div>
      </section>

      <!-- BOTTOM FLOATING CHAT INPUT BAR -->
      <div class="chat-input-bar">
        <span class="chat-sparkle">✨</span>
        <input type="text" id="mainInput" placeholder="Ask OmniPlus or prompt a tool action... (Press Enter)" autofocus />
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

        <div class="action-row" onclick="quickPrompt('Search the web for the latest updates on Python and MCP.')">
          <div class="action-left">
            <div class="action-icon" style="color: #38bdf8;">🌐</div>
            <div class="action-meta">
              <h5>Search the Web</h5>
              <p>Find latest information</p>
            </div>
          </div>
          <span class="chevron-right">›</span>
        </div>

        <div class="action-row" onclick="quickPrompt('Browse project directory files and summarize main modules.')">
          <div class="action-left">
            <div class="action-icon" style="color: #f59e0b;">📁</div>
            <div class="action-meta">
              <h5>Browse Files</h5>
              <p>Check project files</p>
            </div>
          </div>
          <span class="chevron-right">›</span>
        </div>

        <div class="action-row" onclick="quickPrompt('Check GitHub repository status and repository files.')">
          <div class="action-left">
            <div class="action-icon" style="color: #c084fc;">🐙</div>
            <div class="action-meta">
              <h5>Use GitHub</h5>
              <p>Explore repositories</p>
            </div>
          </div>
          <span class="chevron-right">›</span>
        </div>

        <div class="action-row" onclick="quickPrompt('Run loaded MCP tools and show output.')">
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
          <span class="panel-link" onclick="quickPrompt('Summarize recent interactions and tool executions.')">View all</span>
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

    // Time-based greeting (morning/afternoon/evening)
    (function setGreeting() {
      const hour = new Date().getHours();
      const greetingEl = document.getElementById('timeGreeting');
      if (hour >= 5 && hour < 12) greetingEl.textContent = 'morning';
      else if (hour >= 12 && hour < 17) greetingEl.textContent = 'afternoon';
      else greetingEl.textContent = 'evening';
    })();

    mainInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') submitMessage();
    });

    function quickPrompt(text) {
      mainInput.value = text;
      submitMessage();
    }

    function toggleDrawer(show) {
      if (show) {
        chatDrawer.classList.add('open');
      } else {
        chatDrawer.classList.remove('open');
      }
    }

    function selectNav(el, section) {
      document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
      el.classList.add('active');

      if (section === 'files') {
        quickPrompt('List and summarize all directories and key files in this project workspace.');
      } else if (section === 'search') {
        quickPrompt('Perform a search for the latest documentation on Model Context Protocol.');
      } else if (section === 'github') {
        quickPrompt('Inspect the GitHub integration status and repository configuration.');
      } else if (section === 'tools') {
        quickPrompt('List all active MCP tools and demonstrate how each tool functions.');
      } else if (section === 'settings') {
        quickPrompt('Show the current OmniPlus system configuration, active Gemini model, and server status.');
      }
    }

    async function submitMessage() {
      const text = mainInput.value.trim();
      if (!text) return;

      mainInput.value = '';
      toggleDrawer(true);

      // Append user message
      appendMessage('user', text);
      sendBtn.disabled = true;
      sendBtn.innerHTML = '<span class="spinner"></span> Thinking...';

      // Append thinking indicator
      const assistantMsg = appendMessage('assistant', '<span class="spinner"></span> <i>OmniPlus is reasoning & executing MCP tools...</i>');
      chatDrawer.scrollTop = chatDrawer.scrollHeight;

      // Add to recent activity
      logRecentActivity(text);

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Failed to get response');
        }
        assistantMsg.querySelector('.msg-bubble').innerHTML = marked.parse(data.response);
      } catch (err) {
        let msgText = err.message;
        if (msgText.includes('429') || msgText.includes('RESOURCE_EXHAUSTED') || msgText.includes('quota')) {
          msgText = '⏳ <b>Google AI Studio Free Tier rate limit reached.</b><br><br>The free tier allows 5 requests per minute. OmniPlus retried automatically, but the quota window is still active. Please wait <b>10 seconds</b> and try again!';
          assistantMsg.querySelector('.msg-bubble').innerHTML = `<div style="background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.35); padding: 0.85rem; border-radius: 10px; color: #fde68a; font-size: 0.88rem; line-height: 1.5;">${msgText}</div>`;
        } else {
          assistantMsg.querySelector('.msg-bubble').innerHTML = `<p style="color: #f87171;">⚠️ <b>Error:</b> ${msgText}</p>`;
        }
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
        <div class="msg-bubble">${htmlContent.startsWith('<') ? htmlContent : `<p>${htmlContent}</p>`}</div>
      `;
      msgGroup.appendChild(msg);
      return msg;
    }

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

    async function clearAllChat() {
      await fetch('/api/clear', { method: 'POST' });
      msgGroup.innerHTML = '';
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
