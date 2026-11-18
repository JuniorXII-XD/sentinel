from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./sentinel.db"
    trusted_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ]
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]
    cookie_secure: bool = False
    demo_enabled: bool = False
    session_hours: int = 8
    idle_minutes: int = 30
    timezone: str = "Asia/Bangkok"
    work_start: int = 7
    work_end: int = 22

    @model_validator(mode="after")
    def validate_environment(self):
        from zoneinfo import ZoneInfo

        ZoneInfo(self.timezone)
        if not 0 <= self.work_start < self.work_end <= 24:
            raise ValueError("Work hours must be between 0 and 24")
        if not 1 <= self.session_hours <= 24 or not 1 <= self.idle_minutes <= 120:
            raise ValueError("Invalid session lifetime")
        if not self.allowed_hosts or any("*" in host for host in self.allowed_hosts):
            raise ValueError("Explicit allowed hosts required")
        if any(
            not host or host != host.strip() or "/" in host
            for host in self.allowed_hosts
        ):
            raise ValueError(
                "Allowed hosts must be nonempty hostnames without a URL path"
            )
        if not self.trusted_origins or any(
            urlparse(x).scheme not in ("http", "https")
            or not urlparse(x).netloc
            or urlparse(x).path
            or "*" in x
            for x in self.trusted_origins
        ):
            raise ValueError("Explicit origins without trailing slash required")
        if self.environment == "production" and (
            not self.cookie_secure
            or self.demo_enabled
            or any(not x.startswith("https://") for x in self.trusted_origins)
        ):
            raise ValueError(
                "Production requires secure cookies, HTTPS origins and demo disabled"
            )
        if self.environment == "production" and (
            "allowed_hosts" not in self.model_fields_set
            or "testserver" in [host.lower() for host in self.allowed_hosts]
        ):
            raise ValueError(
                "Production requires explicit ALLOWED_HOSTS without testserver"
            )
        return self

    @property
    def cookie_name(self):
        return "__Host-sentinel" if self.cookie_secure else "sentinel_session"


@lru_cache
def get_settings():
    return Settings()
