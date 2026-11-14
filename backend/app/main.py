"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import SessionLocal
from app.routers import (
    api_keys,
    attachments,
    audit,
    auth,
    dashboards,
    defense,
    integration,
    report_templates,
    reports,
    users,
    vulnerabilities,
)
from app.seed import seed_first_admin

DEV_JWT_SECRET = "dev-only-insecure-change-me"


def check_production_config() -> None:
    """Refuse to run in production with settings that are only safe for development."""
    if settings.environment != "production":
        return
    problems = []
    if settings.jwt_secret == DEV_JWT_SECRET or len(settings.jwt_secret) < 32:
        problems.append("JWT_SECRET must be set to a random value of at least 32 characters")
    if problems:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_production_config()
    # First-run admin seed (§10.1). Runs once at startup; no-op if users exist.
    with SessionLocal() as session:
        seed_first_admin(session)
    yield


# The interactive API docs are a development aid; production does not expose them.
_prod = settings.environment == "production"
app = FastAPI(
    title=settings.app_name, lifespan=lifespan,
    docs_url=None if _prod else "/docs", redoc_url=None if _prod else "/redoc",
    openapi_url=None if _prod else "/openapi.json",
)

# NOTE: the backend owns NO "/api" prefix. nginx maps the public "/api/*" to
# the backend root (proxy_pass http://api:8000/), so "/api/auth/login" arrives
# here as "/auth/login". Keep routes prefix-free.
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(vulnerabilities.router)
app.include_router(api_keys.router)
app.include_router(audit.router)
app.include_router(attachments.router)
app.include_router(integration.router)
app.include_router(defense.router)
app.include_router(reports.router)
app.include_router(report_templates.router)
app.include_router(dashboards.router)
app.include_router(dashboards.tv_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. nginx and later monitoring hit this to confirm the API is up."""
    return {"status": "ok", "environment": settings.environment}
