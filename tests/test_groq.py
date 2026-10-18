"""Tests for Groq Cloud LLM provider and multi-provider failover."""
import os
import sys
import subprocess

PYTHON = sys.executable
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_groq_settings():
    from mcp_assistant.config import Settings
    s = Settings(
        gemini_api_key="gemini-key",
        groq_api_key="gsk_test123",
        groq_model="llama-3.3-70b-versatile",
        llm_provider="groq",
    )
    assert s.has_groq() is True
    assert s.has_gemini() is True
    assert s.get_active_provider() == "groq"
    print("✅ test_groq_settings passed")


def test_assistant_groq_initialization():
    from mcp_assistant.config import Settings
    from mcp_assistant.assistant import MCPAssistant
    s = Settings(
        groq_api_key="gsk_dummy_for_test",
        groq_model="llama-3.3-70b-versatile",
        llm_provider="groq",
    )
    assistant = MCPAssistant(s)
    assert assistant.provider == "groq"
    assert assistant.current_model == "llama-3.3-70b-versatile"
    assert "llama-3.1-8b-instant" in assistant._model_pool
    print("✅ test_assistant_groq_initialization passed")


def test_groq_chatgroq_import():
    result = subprocess.run(
        [PYTHON, "-c", "from langchain_groq import ChatGroq; print('ChatGroq OK')"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "ChatGroq OK" in result.stdout
    print("✅ test_groq_chatgroq_import passed")


if __name__ == "__main__":
    test_groq_settings()
    test_assistant_groq_initialization()
    test_groq_chatgroq_import()
    print("\n🎉 Groq Integration ALL TESTS PASSED")
