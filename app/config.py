from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://hw:hwpass@localhost:5432/hwfinal"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "super-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


settings = Settings()