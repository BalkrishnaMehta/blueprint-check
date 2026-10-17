"""Process settings. Environment variables override the project .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict

from blueprint.vision import DEFAULT_MODEL

LOCAL_MODEL = "gemma4:e4b"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = DEFAULT_MODEL
    vision_base_url: str = "http://127.0.0.1:11434/v1"
    vision_model: str = LOCAL_MODEL
    vision_api_key: str = "ollama"


def get_settings() -> Settings:
    return Settings()
