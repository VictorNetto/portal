"""Machine-facing ingest endpoints (SPEC §11).

Authenticated with an API key (`X-API-Key`), never with a user session. API keys
are accepted ONLY here — they cannot reach the UI endpoints, user management or
the audit log, whatever role they carry.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import get_api_key
from app.models.enums import UserRole
from app.models.user import ApiKey
from app.schemas.ingest import IngestResult, IngestVuln
from app.services import ingest as svc

router = APIRouter(prefix="/ingest", tags=["ingest"])

MAX_BODY_BYTES = 1024 * 1024  # 1 MB per request


def _limit_body(request: Request) -> None:
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Payload exceeds 1 MB")


@router.post(
    "/vulnerabilities",
    response_model=IngestResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_limit_body)],
)
def ingest_vulnerability(
    payload: IngestVuln,
    request: Request,
    key: ApiKey = Depends(get_api_key),
    session: Session = Depends(get_session),
) -> IngestResult:
    # Only keys scoped to a writing role may create records.
    if key.role not in (UserRole.admin, UserRole.write_all):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "This API key's role cannot create vulnerabilities"
        )
    vuln = svc.create(session, payload, key, request)
    return IngestResult(id=vuln.id, internal_id=vuln.internal_id, status=vuln.status.value)
