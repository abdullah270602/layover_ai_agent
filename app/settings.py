# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Google APIs
    google_maps_api_key: str = Field(..., env="GOOGLE_MAPS_API_KEY")
    google_genai_api_key: str = Field(..., env="GOOGLE_API_KEY")

    # General App Config
    app_name: str = "Layover Explorer"
    environment: str = Field("development", env="ENVIRONMENT")  # development, staging, production
    debug: bool = Field(True, env="DEBUG")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# instantiate settings
settings = Settings()
