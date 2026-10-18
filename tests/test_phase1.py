"""Phase 1 tests — Core Setup & CLI Shell."""
import subprocess
import sys
import os

PYTHON = sys.executable


def test_imports():
    result = subprocess.run(
        [PYTHON, "-c", "from mcp_assistant.config import Settings, get_settings; print('OK')"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_imports passed")


def test_cli_help():
    result = subprocess.run(
        [PYTHON, "-m", "mcp_assistant.cli", "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "chat" in result.stdout
    assert "run" in result.stdout
    assert "tools" in result.stdout
    print("✅ test_cli_help passed")


def test_missing_api_key():
    env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    # Also unset from dotenv by using a temp dir with no .env
    result = subprocess.run(
        [PYTHON, "-c", "from mcp_assistant.config import get_settings; get_settings.cache_clear(); get_settings()"],
        capture_output=True, text=True, env=env,
        cwd=os.path.expanduser("~"),  # no .env in home dir
    )
    assert result.returncode != 0 or "GEMINI_API_KEY" in result.stderr or "GEMINI_API_KEY" in result.stdout
    print("✅ test_missing_api_key passed")


def test_ui_imports():
    result = subprocess.run(
        [PYTHON, "-c", "from mcp_assistant.ui.display import print_welcome_banner, print_response, print_error; print('OK')"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    print("✅ test_ui_imports passed")


if __name__ == "__main__":
    test_imports()
    test_cli_help()
    test_missing_api_key()
    test_ui_imports()
    print("\n🎉 Phase 1 ALL TESTS PASSED")
