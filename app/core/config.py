from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholder only - anyone who reads this repo knows it, so production must
# set SECRET_KEY in the environment (main.py warns at startup if it isn't).
DEFAULT_SECRET_KEY = "change-this-secret-key-in-production"


class Settings(BaseSettings):
    APP_NAME: str = "Okemzhub Inventory API"
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # Switch to postgresql+psycopg2://user:pass@host/dbname for production
    DATABASE_URL: str = "sqlite:///./okemzhub.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
