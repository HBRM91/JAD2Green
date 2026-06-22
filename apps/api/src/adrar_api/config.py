from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/postgres"
    supabase_jwt_secret: str = "super-secret-jwt-key-for-testing"
    supabase_url: str = ""
    secret_key: str = "dev-secret"


settings = Settings()
