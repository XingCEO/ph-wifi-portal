from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "PH WiFi Portal"
    environment: str = "production"
    secret_key: str = "change-me-in-production"

    # Database — 支援 postgresql:// 和 postgresql+asyncpg:// 兩種格式
    database_url: str = "postgresql+asyncpg://user:pass@localhost/wifi_portal"

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Omada OC200
    omada_host: str = "192.168.1.1"
    omada_port: int = 8043
    omada_controller_id: str = ""
    omada_operator: str = "admin"
    omada_password: str = "admin"

    # Adcash
    adcash_zone_key: str = ""

    # Business Rules
    ad_duration_seconds: int = 30
    session_duration_seconds: int = 3600
    anti_spam_window_seconds: int = 3600

    # Admin
    admin_username: str = "admin"
    admin_password: str = "admin"

    # CORS - allowed origins
    cors_origins: list[str] = ["*"]

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


settings = Settings()
