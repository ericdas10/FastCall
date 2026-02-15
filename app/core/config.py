from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    TEST_DATABASE_URL: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"

settings = Settings()
