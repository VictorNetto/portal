"""Application settings, loaded from environment variables.

pydantic-settings reads values from the process environment (which Docker
Compose populates from the .env file). Every setting has a type; invalid or
missing required values fail loudly at startup rather than silently at runtime.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    app_name: str = "Red Team Operations Platform"
    environment: str = "development"  # development | production

    # --- Database (populated by Compose; see .env.example) ---
    # Async URL used by SQLAlchemy. Host "db" is the Compose service name.
    database_url: str = "postgresql+psycopg://portal:portal@db:5432/portal"

    # --- Object storage (MinIO) ---
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "portal"
    minio_secret_key: str = "portal-dev-secret"
    minio_bucket: str = "attachments"
    minio_secure: bool = False  # True once TLS is in front of MinIO


settings = Settings()
