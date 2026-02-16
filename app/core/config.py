# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "FastCall API"
    ENV: str = "dev"  # dev|prod

    # Database
    DATABASE_URL: str
    TEST_DATABASE_URL: str

    # JWT (python-jose)
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

settings = Settings()
