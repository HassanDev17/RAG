from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "RAG"
    log_level: str = "INFO"
    llm_provider: str = "google"
    llm_api_key: str = ""
    llm_model: str = "gemini-3.6-flash"


@lru_cache
def get_settings() -> Settings:
    return Settings()
