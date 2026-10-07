"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import SessionLocal
from app.routers import auth, users, vulnerabilities
from app.seed import seed_first_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # First-run admin seed (§10.1). Runs once at startup; no-op if users exist.
    with SessionLocal() as session:
        seed_first_admin(session)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# NOTE: the backend owns NO "/api" prefix. nginx maps the public "/api/*" to
# the backend root (proxy_pass http://api:8000/), so "/api/auth/login" arrives
# here as "/auth/login". Keep routes prefix-free.
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(vulnerabilities.router)
app.include_router(vulnerabilities.rvs_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. nginx and later monitoring hit this to confirm the API is up."""
    return {"status": "ok", "environment": settings.environment}
