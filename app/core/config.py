from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

try:
    from dotenv import load_dotenv
    from pathlib import Path

    # Prefer `app/.env` (common in this repo), but fall back to root `.env`.
    this_dir = Path(__file__).resolve().parent  # app/core
    app_dir = this_dir.parent  # app
    repo_dir = app_dir.parent

    env_app = app_dir / ".env"
    env_repo = repo_dir / ".env"

    load_dotenv(dotenv_path=str(env_app) if env_app.exists() else str(env_repo), override=False)
except Exception:
    # Dev convenience: ignore if python-dotenv isn't available or no .env file exists.
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    APP_ENV: str = "development"


    # DATABASE_URL: str = "postgresql+psycopg2://smart_job_tracker:smart_job_tracker_password@postgres:5432/smart_job_tracker"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:Annie@localhost:5432/smart_job_tracker"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "change-me-super-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    CORS_ORIGINS: str = ""

    # Celery (background jobs)
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"
    CELERY_TIMEZONE: str = "UTC"

    # SMTP (automation layer)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""


settings = Settings()

# Note:
# We pass defaults so the Settings object can be imported without crashing in tooling.
# In actual runs, environment variables from `.env` / Docker Compose override these.

