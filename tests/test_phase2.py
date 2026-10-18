"""Phase 2 tests — Filesystem MCP server configuration."""
import subprocess
import sys
import json

PYTHON = sys.executable


def test_filesystem_server_config():
    result = subprocess.run(
        [PYTHON, "-c", """
from mcp_assistant.servers.filesystem import FilesystemServer
from pathlib import Path
import json

server = FilesystemServer()
config = server.get_server_config()
print(json.dumps(config))
assert config['command'] == 'npx'
assert '@modelcontextprotocol/server-filesystem' in config['args']
assert config['transport'] == 'stdio'
print('OK')
"""],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_filesystem_server_config passed")
    print(" ", result.stdout.strip())


def test_config_builder_includes_filesystem():
    result = subprocess.run(
        [PYTHON, "-c", """
import os, json
os.environ['GEMINI_API_KEY'] = 'test-key-for-testing'
from mcp_assistant.config import Settings
from mcp_assistant.servers.config_builder import build_mcp_config
settings = Settings(gemini_api_key='test-key')
config = build_mcp_config(settings)
print(json.dumps(list(config.keys())))
assert 'filesystem' in config
assert 'websearch' in config
assert 'github' not in config  # no token
print('OK')
"""],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_config_builder_includes_filesystem passed")


def test_config_builder_includes_github_when_token():
    result = subprocess.run(
        [PYTHON, "-c", """
import os, json
from mcp_assistant.config import Settings
from mcp_assistant.servers.config_builder import build_mcp_config
settings = Settings(gemini_api_key='test-key', github_token='ghp_test')
config = build_mcp_config(settings)
assert 'github' in config
print('OK')
"""],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_config_builder_includes_github_when_token passed")


if __name__ == "__main__":
    test_filesystem_server_config()
    test_config_builder_includes_filesystem()
    test_config_builder_includes_github_when_token()
    print("\n🎉 Phase 2 ALL TESTS PASSED")
