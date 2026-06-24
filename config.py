from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    REDIS_URL: str = "redis://localhost:6379"
    ENVIRONMENT: str = "development"
    ODDS_UPDATE_INTERVAL_SECONDS: int = 5
    RESULT_DELAY_MINUTES: int = 90
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    model_config = {"env_file": ".env"}


settings = Settings()
