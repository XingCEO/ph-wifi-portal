import os
from pydantic_settings import BaseSettings


def _get_database_url() -> str:
    """支援多種 Zeabur 注入的資料庫變數名稱"""
    for key in ["DATABASE_URL", "POSTGRES_URI", "POSTGRESQL_URI", "POSTGRES_CONNECTION_STRING"]:
        val = os.environ.get(key, "")
        if val and not val.startswith("${"):
            return val
    return "postgresql+asyncpg://user:pass@localhost/wifi_portal"


def _get_redis_url() -> str:
    """支援多種 Zeabur 注入的 Redis 變數名稱"""
    for key in ["REDIS_URL", "REDIS_URI", "REDIS_CONNECTION_STRING"]:
        val = os.environ.get(key, "")
        if val and not val.startswith("${"):
            return val
    return "redis://localhost:6379/0"


import warnings


class Settings(BaseSettings):
    # App
    app_name: str = "PH WiFi Portal"
    environment: str = "production"
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost/wifi_portal"

    @property
    def async_database_url(self) -> str:
        url = _get_database_url()
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    @property
    def resolved_redis_url(self) -> str:
        return _get_redis_url()

    # Omada OC200
    omada_host: str = "192.168.1.1"
    omada_port: int = 8043
    omada_controller_id: str = ""
    omada_operator: str = "admin"
    omada_password: str = ""
    omada_verify_ssl: bool = False

    # Adcash
    adcash_zone_key: str = ""

    # Business Rules
    ad_duration_seconds: int = 10
    session_duration_seconds: int = 3600
    anti_spam_window_seconds: int = 10

    # Admin
    admin_username: str = "admin"
    admin_password: str = ""

    # CORS - allowed origins (set via env var in production)
    cors_origins: list[str] = []

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


settings = Settings()


def validate_settings() -> None:
    """Validate settings on startup. Raise RuntimeError for insecure defaults in production."""
    # Bounds validation for business rules (all environments)
    if not (1 <= settings.ad_duration_seconds <= 300):
        raise RuntimeError(f"ad_duration_seconds must be 1-300, got {settings.ad_duration_seconds}")
    if not (60 <= settings.session_duration_seconds <= 86400):
        raise RuntimeError(f"session_duration_seconds must be 60-86400, got {settings.session_duration_seconds}")
    if not (1 <= settings.anti_spam_window_seconds <= 86400):
        raise RuntimeError(f"anti_spam_window_seconds must be 1-86400, got {settings.anti_spam_window_seconds}")

    if settings.environment == "production":
        if settings.secret_key == "change-me-in-production":
            raise RuntimeError("SECRET_KEY is using the default value — set it in .env before running in production")
        if not settings.admin_password:
            raise RuntimeError("ADMIN_PASSWORD is empty — set it in .env before running in production")
        if settings.cors_origins == ["*"]:
            warnings.warn("CORS_ORIGINS allows all origins — restrict in production", stacklevel=2)
