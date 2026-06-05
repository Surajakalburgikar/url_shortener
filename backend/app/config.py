"""
app/config.py
─────────────
Central configuration using Pydantic BaseSettings (12-Factor App pattern).

How it works:
- Pydantic reads every field from environment variables automatically.
- If a required field is missing at startup, the app crashes immediately with a
  clear error message — better than crashing on the first request.
- The `@lru_cache` decorator means we only read the .env file ONCE, then reuse
  the same Settings object for the lifetime of the app (performance win).
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application configuration, sourced from environment variables."""

    # ── Model config ─────────────────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",          # Look for a .env file in the working directory
        env_file_encoding="utf-8",
        case_sensitive=False,     # APP_ENV and app_env are treated the same
        extra="ignore",           # Silently ignore unknown env vars (don't crash)
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: Literal["development", "testing", "production"] = "development"
    app_version: str = "1.0.0"
    docs_username: str = "admin"
    docs_password: str = "admin"

    # ── Security ──────────────────────────────────────────────────────────────
    secret_key: str = Field(..., min_length=32)   # ... means REQUIRED — no default
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(...)
    test_database_url: str = ""

    @field_validator("database_url", mode="after")
    @classmethod
    def append_prepared_statement_cache_size(cls, v: str) -> str:
        if v.startswith("postgresql+asyncpg://") and "prepared_statement_cache_size" not in v:
            separator = "&" if "?" in v else "?"
            return f"{v}{separator}prepared_statement_cache_size=0"
        return v

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = ""

    # ── GitHub OAuth ──────────────────────────────────────────────────────────
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/api/v1/auth/github/callback"

    # ── CORS / Frontend ───────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:5173"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,https://url-shortener-mu-lilac.vercel.app"

    # ── API ───────────────────────────────────────────────────────────────────
    api_version: str = "v1"

    # ── Computed properties ───────────────────────────────────────────────────
    @property
    def allowed_origins_list(self) -> list[str]:
        """Convert comma-separated ALLOWED_ORIGINS string into a Python list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"


@lru_cache  # Called once — result cached for app lifetime
def get_settings() -> Settings:
    """
    Return the application settings singleton.

    Usage in FastAPI endpoints:
        from app.config import get_settings
        settings = get_settings()

    Usage as a FastAPI dependency:
        from fastapi import Depends
        def my_endpoint(settings: Settings = Depends(get_settings)):
            ...
    """
    return Settings()


# Convenience alias — import `settings` directly for non-DI usage
settings: Settings = get_settings()
