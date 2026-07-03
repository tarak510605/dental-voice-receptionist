"""
Application settings loaded from environment variables via pydantic-settings.
All secrets must be provided through the .env file — never hardcode credentials.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "QuensultingAI Dental Clinic AI Receptionist"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Google Sheets ─────────────────────────────────────────────────────────
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = "credentials.json"
    GOOGLE_SHEETS_SPREADSHEET_ID: str = ""
    GOOGLE_SHEETS_WORKSHEET_NAME: str = "Appointments"

    # ── Gmail SMTP ────────────────────────────────────────────────────────────
    GMAIL_SENDER_EMAIL: str = ""
    GMAIL_APP_PASSWORD: str = ""
    GMAIL_SENDER_NAME: str = "QuensultingAI Dental Clinic"

    # ── RetellAI ──────────────────────────────────────────────────────────────
    RETELL_API_KEY: str = ""
    RETELL_WEBHOOK_SECRET: str = ""
    RETELL_AGENT_ID: str = ""

    # ── Clinic Configuration ──────────────────────────────────────────────────
    TIMEZONE: str = "Asia/Kolkata"
    SLOT_DURATION_MINUTES: int = 30

    # ── Retry Configuration ───────────────────────────────────────────────────
    SHEETS_MAX_RETRIES: int = 3
    SHEETS_RETRY_DELAY_SECONDS: float = 1.0

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton of Settings."""
    return Settings()
