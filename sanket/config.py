"""Settings read from environment variables with the SANKET_ prefix."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Run-time configuration. Override any field with SANKET_<NAME>."""

    model_config = SettingsConfigDict(env_prefix="SANKET_")

    db_url: str = f"sqlite:///{ROOT / 'sanket.db'}"
    artifacts_dir: Path = ROOT / "artifacts"
    data_dir: Path = ROOT / "data"
    cors_origins: str = "http://localhost:5173"
    max_chars: int = 2000
    max_tickets: int = 5000
    seed: int = 42


def get_settings() -> Settings:
    """Build settings fresh so tests can change the environment."""
    return Settings()
