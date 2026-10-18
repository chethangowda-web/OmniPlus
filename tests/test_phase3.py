"""Phase 3 tests — Web Search MCP server."""
import subprocess
import sys
from pathlib import Path

PYTHON = sys.executable
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_websearch_config():
    result = subprocess.run(
        [PYTHON, "-c", """
from mcp_assistant.servers.websearch import WebSearchServer
config = WebSearchServer().get_server_config()
print(config)
assert config['transport'] == 'stdio'
print('OK')
"""],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_websearch_config passed")


def test_ddg_server_exists():
    ddg_server = Path("src/mcp_assistant/servers/_ddg_server.py")
    assert ddg_server.exists(), f"Missing: {ddg_server}"
    content = ddg_server.read_text()
    assert "web_search" in content
    assert "DDGS" in content or "duckduckgo" in content.lower()
    print("✅ test_ddg_server_exists passed")


def test_ddg_import():
    result = subprocess.run(
        [PYTHON, "-c", "from duckduckgo_search import DDGS; print('OK')"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_ddg_import passed")


def test_ddg_server_syntax():
    result = subprocess.run(
        [PYTHON, "-m", "py_compile", "src/mcp_assistant/servers/_ddg_server.py"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_ddg_server_syntax passed")


if __name__ == "__main__":
    test_websearch_config()
    test_ddg_server_exists()
    test_ddg_import()
    test_ddg_server_syntax()
    print("\n🎉 Phase 3 ALL TESTS PASSED")
