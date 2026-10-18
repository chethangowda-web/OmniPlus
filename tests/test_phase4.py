"""Phase 4 tests — GitHub MCP server."""
import subprocess
import sys

PYTHON = sys.executable
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_github_server_config():
    result = subprocess.run(
        [PYTHON, "-c", """
from mcp_assistant.servers.github import GitHubServer
config = GitHubServer(github_token='ghp_test123').get_server_config()
print(config)
assert config['command'] == 'npx'
assert '@modelcontextprotocol/server-github' in config['args']
assert config['transport'] == 'stdio'
# Token should be passed via env
assert 'env' in config
assert config['env'].get('GITHUB_PERSONAL_ACCESS_TOKEN') == 'ghp_test123'
print('OK')
"""],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_github_server_config passed")


def test_github_not_in_config_without_token():
    result = subprocess.run(
        [PYTHON, "-c", """
from mcp_assistant.config import Settings
from mcp_assistant.servers.config_builder import build_mcp_config
s = Settings(gemini_api_key='test')
config = build_mcp_config(s)
assert 'github' not in config, f'Expected no github, got: {list(config.keys())}'
print('OK — github correctly absent without token')
"""],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_github_not_in_config_without_token passed")


def test_github_in_config_with_token():
    result = subprocess.run(
        [PYTHON, "-c", """
from mcp_assistant.config import Settings
from mcp_assistant.servers.config_builder import build_mcp_config
s = Settings(gemini_api_key='test', github_token='ghp_test')
config = build_mcp_config(s)
assert 'github' in config
print('OK — github correctly present with token')
"""],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_github_in_config_with_token passed")


if __name__ == "__main__":
    test_github_server_config()
    test_github_not_in_config_without_token()
    test_github_in_config_with_token()
    print("\n🎉 Phase 4 ALL TESTS PASSED")
