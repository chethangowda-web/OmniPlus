"""Phase 5 tests — Polish & UX features."""
import subprocess
import sys
import json
import os
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PYTHON = sys.executable


def test_history_attribute():
    result = subprocess.run(
        [PYTHON, "-c", """
import os
os.environ['GEMINI_API_KEY'] = 'test'
from mcp_assistant.config import Settings
from mcp_assistant.assistant import MCPAssistant
s = Settings(gemini_api_key='test')
a = MCPAssistant(s)
assert hasattr(a, '_history')
assert isinstance(a._history, list)
a.clear_history()
assert a._history == []
print('OK')
"""],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_history_attribute passed")


def test_save_history():
    result = subprocess.run(
        [PYTHON, "-c", """
import os, json
from pathlib import Path
os.environ['GEMINI_API_KEY'] = 'test'
from mcp_assistant.config import Settings
from mcp_assistant.assistant import MCPAssistant
s = Settings(gemini_api_key='test')
a = MCPAssistant(s)
a._history = [('human', 'hello'), ('assistant', 'hi there')]
a.save_history()
hf = Path.home() / '.mcp-assistant' / 'history.json'
assert hf.exists()
data = json.loads(hf.read_text(encoding='utf-8'))
assert len(data) == 2
assert data[0]['role'] == 'human'
print('OK')
"""],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_save_history passed")


def test_config_command():
    result = subprocess.run(
        [PYTHON, "-m", "mcp_assistant.cli", "config", "--help"],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_config_command passed")


def test_print_tool_call():
    result = subprocess.run(
        [PYTHON, "-c", """
from mcp_assistant.ui.display import print_tool_call
print_tool_call('web_search')
print('OK')
"""],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_print_tool_call passed")


def test_slash_command_in_cli_module():
    src = Path("src/mcp_assistant/cli.py").read_text(encoding="utf-8")
    assert "/help" in src, "Missing /help slash command"
    assert "/tools" in src, "Missing /tools slash command"
    assert "/clear" in src, "Missing /clear slash command"
    print("✅ test_slash_command_in_cli_module passed")


if __name__ == "__main__":
    test_history_attribute()
    test_save_history()
    test_config_command()
    test_print_tool_call()
    test_slash_command_in_cli_module()
    print("\n🎉 Phase 5 ALL TESTS PASSED")
