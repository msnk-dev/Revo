from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider_order: str = "hf,groq"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    groq_router_model: str = "openai/gpt-oss-20b"
    hf_token: str | None = None
    hf_model: str = "Qwen/Qwen3.8-27B:fastest"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = ""
    ollama_api_key: str = "ollama"
    llm_timeout_s: float = Field(default=20, gt=0, le=120)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    llm_daily_token_budget: int = Field(default=100_000, ge=0)

    def provider_order(self) -> list[str]:
        return [name.strip().lower() for name in self.llm_provider_order.split(",") if name.strip()]


@lru_cache
def get_ai_settings() -> AISettings:
    return AISettings()


settings = get_ai_settings()
