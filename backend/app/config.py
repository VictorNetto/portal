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

    # --- Auth / JWT ---
    # Secret for signing JWTs. MUST be overridden in production via env; the
    # default exists only so local dev runs out of the box.
    jwt_secret: str = "dev-only-insecure-change-me"
    jwt_algorithm: str = "HS256"
    # A session lasts at most session_max_minutes from login, and ends earlier
    # after session_idle_minutes without activity: the refresh token only lives
    # that long and is renewed while the user is active (D12).
    session_max_minutes: int = 60
    session_idle_minutes: int = 15
    access_token_ttl_minutes: int = 5

    # First-run admin seed (§10.1). If no users exist on startup, an admin is
    # created. If no password is provided here, a random one is generated and
    # printed to stdout once.
    first_admin_username: str = "admin"
    first_admin_password: str | None = None

    # --- Database (populated by Compose; see .env.example) ---
    # Async URL used by SQLAlchemy. Host "db" is the Compose service name.
    database_url: str = "postgresql+psycopg://portal:portal@db:5432/portal"

    # --- Object storage ---
    # "local" keeps files on a volume (default, no extra service). "s3" uses an
    # S3-compatible server (MinIO per the spec) configured by the minio_* values.
    storage_backend: str = "local"  # local | s3
    storage_local_path: str = "/data/attachments"
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "portal"
    minio_secret_key: str = "portal-dev-secret"
    minio_bucket: str = "attachments"
    minio_secure: bool = False  # True once TLS is in front of MinIO

    # --- Dispatch (SPEC §12) ---
    # "stub" only logs (default, safe for dev). "smtp" sends real email.
    dispatch_transport: str = "stub"  # stub | smtp
    # Comma-separated recipients of every dispatch package.
    dispatch_to: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_starttls: bool = True   # upgrade a plain connection (port 587)
    smtp_ssl: bool = False       # implicit TLS from the start (port 465)
    smtp_timeout_seconds: int = 60


settings = Settings()
