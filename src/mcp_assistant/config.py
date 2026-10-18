"""Configuration module for MCP AI Assistant.

Loads settings from environment variables (via .env file) and exposes
a singleton Settings dataclass for use throughout the application.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

# Load .env file from the current working directory or parent directories
load_dotenv()


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    github_token: str | None = None
    gitlab_token: str | None = None
    gitlab_url: str = "https://gitlab.com"

    def has_github(self) -> bool:
        """Return True if GitHub integration is available with a valid token."""
        if not self.github_token:
            return False
        token = self.github_token.strip()
        return bool(token and not token.startswith("your_") and token.lower() != "none")

    def has_gitlab(self) -> bool:
        """Return True if GitLab integration is available with a valid token."""
        if not self.gitlab_token:
            return False
        token = self.gitlab_token.strip()
        return bool(token and not token.startswith("your_") and token.lower() != "none")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance.

    Raises:
        EnvironmentError: If GEMINI_API_KEY is not set.
    """
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not gemini_api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Please copy .env.example to .env and add your Gemini API key.\n"
            "Get one at: https://aistudio.google.com/app/apikey"
        )

    return Settings(
        gemini_api_key=gemini_api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
        github_token=os.getenv("GITHUB_TOKEN") or None,
        gitlab_token=os.getenv("GITLAB_TOKEN") or None,
        gitlab_url=os.getenv("GITLAB_URL", "https://gitlab.com").strip(),
    )
