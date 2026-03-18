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
        # Prefer the value pydantic-settings resolved from .env / env vars
        url = self.database_url
        # Fallback: check Zeabur-injected env var names
        if url == "postgresql+asyncpg://user:pass@localhost/wifi_portal":
            env_url = _get_database_url()
            if env_url != url:
                url = env_url
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

    # Omada Controller (Docker 同機: "omada" | 遠端 VPS: IP | 硬體 OC200: LAN IP)
    omada_host: str = ""
    omada_port: int = 8043
    omada_controller_id: str = ""
    omada_operator: str = "admin"
    omada_password: str = ""
    omada_verify_ssl: bool = False

    # Adcash
    adcash_zone_key: str = ""

    # Business Rules (aligned with VPA-005 and ADV-004)
    ad_duration_seconds: int = 30           # VPA-005: 30-sec forced video view
    session_duration_seconds: int = 600     # 10 minutes free WiFi access
    anti_spam_window_seconds: int = 3600    # VPA-005 Art.1.5: 60-min MAC dedup

    # CPV Rates in PHP (ADV-004 Art.4.2 / VPA-005 Art.6.2)
    cpv_video_php: float = 3.00             # Video Ad (30 sec, forced view)
    cpv_image_php: float = 2.00             # Image/Banner Ad (15 sec display)

    # Revenue Share (VPA-005 Art.6.2): 50/50 split
    revenue_share_partner_pct: float = 50.0
    revenue_share_platform_pct: float = 50.0

    # Minimum views threshold for revenue share (VPA-005 Art.6.3.3)
    min_monthly_views_for_revenue: int = 2000

    # Data Retention in days (AKD-POL-004 Sec.4)
    retention_connection_logs_days: int = 180    # Connection logs
    retention_ad_data_days: int = 730            # Ad interaction data (24 months)
    retention_security_records_days: int = 1825  # Security incidents (5 years)

    # Monthly Fee PHP (VPA-005 Art.6.1)
    monthly_fee_equipment_php: float = 800.0
    monthly_fee_platform_php: float = 700.0

    # DPO Contact (AKD-POL-004)
    dpo_email: str = "privacy@abotkamay.net"

    # Admin
    admin_username: str = "admin"
    admin_password: str = ""

    # CORS - allowed origins (set via env var in production)
    cors_origins: list[str] = []

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
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
