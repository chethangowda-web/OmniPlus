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

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    llm_provider: str = "groq"
    github_token: str | None = None
    gitlab_token: str | None = None
    gitlab_url: str = "https://gitlab.com"

    def has_groq(self) -> bool:
        """Return True if Groq integration is available with a valid key."""
        if not self.groq_api_key:
            return False
        token = self.groq_api_key.strip()
        return bool(token and not token.startswith("your_") and token.lower() != "none")

    def has_gemini(self) -> bool:
        """Return True if Gemini integration is available with a valid key."""
        if not self.gemini_api_key:
            return False
        token = self.gemini_api_key.strip()
        return bool(token and not token.startswith("your_") and token.lower() != "none")

    def get_active_provider(self) -> str:
        """Return active LLM provider ('groq' or 'gemini')."""
        prov = (self.llm_provider or "").strip().lower()
        if prov == "groq" and self.has_groq():
            return "groq"
        if prov == "gemini" and self.has_gemini():
            return "gemini"
        if self.has_groq():
            return "groq"
        if self.has_gemini():
            return "gemini"
        return prov or "groq"

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
        EnvironmentError: If neither GROQ_API_KEY nor GEMINI_API_KEY is set.
    """
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    llm_provider = os.getenv("LLM_PROVIDER", "").strip().lower()

    if not groq_api_key and not gemini_api_key:
        raise EnvironmentError(
            "Neither GROQ_API_KEY nor GEMINI_API_KEY is set. "
            "Please copy .env.example to .env and configure your Groq or Gemini API key.\n"
            "• Free Groq API Key (14,400 req/day): https://console.groq.com/keys\n"
            "• Google Gemini API Key: https://aistudio.google.com/app/apikey"
        )

    if not llm_provider:
        if groq_api_key and not groq_api_key.startswith("your_"):
            llm_provider = "groq"
        elif gemini_api_key and not gemini_api_key.startswith("your_"):
            llm_provider = "gemini"
        else:
            llm_provider = "groq"

    return Settings(
        gemini_api_key=gemini_api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip(),
        groq_api_key=groq_api_key or None,
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip(),
        llm_provider=llm_provider,
        github_token=os.getenv("GITHUB_TOKEN") or None,
        gitlab_token=os.getenv("GITLAB_TOKEN") or None,
        gitlab_url=os.getenv("GITLAB_URL", "https://gitlab.com").strip(),
    )
