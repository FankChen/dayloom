from pathlib import Path

from pydantic import SecretStr
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
    model_provider: str = "DemoProvider"
    model_base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4.1-mini"
    model_api_key: SecretStr = SecretStr("")
    worker_poll_seconds: float = 2.0
    worker_lease_seconds: float = 120.0
    static_dir: Path = Path("apps/web/dist")
