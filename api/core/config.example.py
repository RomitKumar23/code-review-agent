from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # GitHub
    github_webhook_secret: str
    github_app_token: str 

    # LLM Providers (fill in only the ones you have)
    openai_api_key: str 
    anthropic_api_key: str = ""
    ollama_base_url: str 

    # Active LLM — change this env var to switch providers, no code changes needed
    active_llm_provider: str = "openai"   # openai | anthropic | ollama
    active_llm_model: str = "gpt-4o"

    # PostgreSQL — matches docker-compose.yml db service
    database_url: str

    # Redis — broker + result backend for Celery
    redis_url: str = "redis://redis:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


@lru_cache          # parsed once at startup, reused everywhere
def get_settings() -> Settings:
    return Settings()
