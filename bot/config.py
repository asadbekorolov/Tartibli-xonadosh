from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Production Application Settings loaded from .env file or environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram Bot Live Credentials
    BOT_TOKEN: str = "9246474249:AAHRGaZ65FlU3vUpyqv3vT9qlBcLjX-Hej4"
    BOT_NAME: str = "TartibliXonadoshBot"

    # Database Configuration (PostgreSQL with asyncpg)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "tartibli_db"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/tartibli_db"

    # Redis Configuration (Aiogram FSM Storage & Scheduler Cache)
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://redis:6379/0"

    # Application Timezone & Limits
    TIMEZONE: str = "Asia/Tashkent"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True
    MIN_MEMBERS_PER_FLAT: int = 2
    MAX_MEMBERS_PER_FLAT: int = 10


@lru_cache()
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()
