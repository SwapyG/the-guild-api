# app/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Defines the application's settings, loaded from environment variables.
    Uses Field aliases to map uppercase env vars to lowercase Python attributes.
    """

    database_url: str = Field(..., alias="DATABASE_URL")
    secret_key: str = Field(..., alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Pydantic v2 configuration using a dict
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


# A single, importable instance of our settings
settings = Settings()
