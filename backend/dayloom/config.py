from pathlib import Path

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DAYLOOM_",
        env_file=".env",
        extra="ignore",
        validate_assignment=True,
    )

    database_url: str = "sqlite:///data/dayloom.db"
    access_token: SecretStr = SecretStr("")
    production: bool = False
    auth_backend: str = "LocalAccess"
    public_url: str = "http://127.0.0.1:5178"
    oidc_issuer: str = ""
    oidc_client_id: str = "dayloom"
    oidc_client_secret: SecretStr = SecretStr("")
    oidc_allow_http: bool = False
    native_callback_url: str = "app.dayloom.personal://auth/callback"
    credential_key: SecretStr = SecretStr("")
    credential_key_file: Path = Path("data/credentials.key")
    session_seconds: int = 900
    refresh_seconds: int = 2592000
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "capacitor://localhost",
        "https://localhost",
    ]
    model_provider: str = "UnconfiguredProvider"
    model_base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4.1-mini"
    model_api_key: SecretStr = SecretStr("")
    model_max_tokens: int = 2400
    model_user_providers: list[str] = ["OpenAIProvider"]
    model_allowed_origins: list[str] = [
        "https://api.openai.com",
        "https://api.deepseek.com",
        "https://generativelanguage.googleapis.com",
    ]
    smtp_servers: dict[str, str] = {
        "smtp.gmail.com": "SmtpSsl",
        "smtp.qq.com": "SmtpSsl",
        "smtp.163.com": "SmtpSsl",
        "smtp.office365.com": "SmtpStartTls",
    }
    mail_daily_limit: int = 20
    web_search_enabled: bool = True
    web_search_daily_limit: int = 50
    mcp_allowed_servers: list[str] = []
    device_daily_limit: int = 30
    browser_runner_url: str = ""
    browser_shared_token: SecretStr = SecretStr("")
    browser_allowed_origins: list[str] = []
    worker_poll_seconds: float = 2.0
    worker_lease_seconds: float = 120.0
    static_dir: Path = Path("apps/web/dist")

    @model_validator(mode="after")
    def production_requirements(self):
        if self.production:
            if self.auth_backend != "OidcAccess" or not self.database_url.startswith("postgresql"):
                raise ValueError("Production requires OIDC accounts and PostgreSQL")
            if (
                not self.public_url.startswith("https://")
                or not self.oidc_issuer.startswith("https://")
                or self.oidc_allow_http
            ):
                raise ValueError("Production requires HTTPS application and identity endpoints")
            if not self.credential_key.get_secret_value():
                raise ValueError("Production requires an externally managed credential key")
        return self
