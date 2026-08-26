from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "RAG"
    log_level: str = "INFO"
    llm_provider: str = "google"
    llm_api_key: str = ""
    llm_model: str = "gemini-3.6-flash"

    embedding_model: str = "models/gemini-embedding-001"

    notion_api_key: str = ""
    supabase_db_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
