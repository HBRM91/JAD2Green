from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict

_WEAK_SECRETS = {
    "super-secret-jwt-key-for-testing",
    "dev-secret",
    "",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/postgres"
    supabase_jwt_secret: str = "super-secret-jwt-key-for-testing"
    supabase_url: str = ""
    secret_key: str = "dev-secret"

    def model_post_init(self, __context: object) -> None:
        # Fail fast if production-like environment uses known-weak secrets.
        # Tests override these explicitly via conftest; skip check when ADRAR_TESTING=1.
        if os.getenv("ADRAR_TESTING") == "1":
            return
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production":
            if self.supabase_jwt_secret in _WEAK_SECRETS:
                raise RuntimeError(
                    "FATAL: supabase_jwt_secret is set to a known-weak default. "
                    "Set a real secret in the environment before starting in production."
                )
            if self.secret_key in _WEAK_SECRETS:
                raise RuntimeError(
                    "FATAL: secret_key is set to a known-weak default. "
                    "Set a real secret in the environment before starting in production."
                )


settings = Settings()
