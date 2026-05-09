from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Agent Orchestration Platform"
    database_url: str = "sqlite:///./agent_orchestrator.db"
    llm_provider: str = "gemini"
    google_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    default_model: str = "gemini-1.5-flash"
    telegram_bot_token: str = ""
    embedding_dimensions: int = 64

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
