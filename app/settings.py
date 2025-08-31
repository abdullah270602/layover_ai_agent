from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Google APIs
    GOOGLE_MAPS_API_KEY: str = Field(..., env="GOOGLE_MAPS_API_KEY")
    GOOGLE_GENAI_API_KEY: str = Field(..., env="GOOGLE_GENAI_API_KEY")



    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# instantiate settings
settings = Settings()
