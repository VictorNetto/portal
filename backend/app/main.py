"""FastAPI application entry point.

For the skeleton this exposes only a health check so we can confirm the whole
Docker stack is wired correctly end-to-end. Routers, auth, and the data model
are layered on top of this once the skeleton runs.
"""

from fastapi import FastAPI

from app.config import settings

app = FastAPI(title=settings.app_name)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. nginx and later monitoring hit this to confirm the API is up."""
    return {"status": "ok", "environment": settings.environment}
