"""Application settings read once from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    data_dir: str = "./data"
    claude_model: str = "claude-opus-5-5"
    embedding_model: str = ""
    api_key: str = ""
    max_upload_mb: int = 10
    top_k: int = 5
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
