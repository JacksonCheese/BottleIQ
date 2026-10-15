from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env", extra="ignore"
    )
    database_url: str = "postgresql+psycopg://bottleiq:bottleiq@localhost:5432/bottleiq"
    web_origin: str = "http://localhost:3000"
    environment: str = "development"
    demo_enabled: bool = False
    cookie_secure: bool = False
    max_upload_bytes: int = 10 * 1024 * 1024
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""


@lru_cache
def settings() -> Settings:
    config = Settings()
    if config.environment == "production" and (not config.cookie_secure or config.demo_enabled):
        raise ValueError("Production requires COOKIE_SECURE=true and DEMO_ENABLED=false")
    if config.environment == "production" and not (config.smtp_host and config.smtp_from):
        raise ValueError("Production requires SMTP_HOST and SMTP_FROM for recovery and invitations")
    if config.environment == "production" and not config.web_origin.startswith("https://"):
        raise ValueError("Production requires an HTTPS WEB_ORIGIN")
    return config
