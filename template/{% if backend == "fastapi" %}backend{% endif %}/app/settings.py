"""Réglages du backend, lus dans l'environnement et `.env` ([SECRETS])."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    debug: bool = False
    allowed_origins: list[str] = []


@lru_cache
def get_settings() -> Settings:
    return Settings()
