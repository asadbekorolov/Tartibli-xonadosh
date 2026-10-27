from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application runtime configuration loaded from environment variables (.env).
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram Bot
    BOT_TOKEN: str = "9246474249:AAHRGaZ65FlU3vUpyqv3vT9qlBcLjX-Hej4"
    BOT_NAME: str = "TartibliXonadoshBot"

    # PostgreSQL Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "tartibli_db"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tartibli_db"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://localhost:6379/0"

    # App Settings
    TIMEZONE: str = "Asia/Tashkent"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True

    # Flat Constraints (Cohorts of 7-10 students)
    MAX_MEMBERS_PER_FLAT: int = 10


@lru_cache()
def get_settings() -> Settings:
    return Settings()
