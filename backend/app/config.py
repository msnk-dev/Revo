from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Revo"
    app_env: str = "development"
    app_currency: str = "INR"
    app_secret_key: str = Field(default="local-development-secret-change-this-key", min_length=32)
    database_url: str = "postgresql+psycopg://revo:revo@localhost:5432/revo"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "noreply@revo.local"
    cors_origins: str = "http://localhost:5173"
    enable_scheduler: bool = False

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_cors(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins or "*" in origins:
            raise ValueError("CORS_ORIGINS must contain explicit origins and cannot use a wildcard")
        return ",".join(origins)

    @model_validator(mode="after")
    def enforce_production_secret(self):
        if self.app_env.lower() == "production" and (
            self.app_secret_key == "local-development-secret-change-this-key"
            or "replace-this" in self.app_secret_key.lower()
        ):
            raise ValueError("APP_SECRET_KEY must be set to a private value in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

