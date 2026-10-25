"""Audit-logging helper.

Writes append-only entries to `audit_logs` (SPEC §10.3, §15.11). Captures the
real client IP from the proxy headers nginx sets (X-Forwarded-For / X-Real-IP;
see docs/DEPLOYMENT.md §4) — without this, every entry would log nginx's IP.
"""

import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction


def client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    # X-Forwarded-For may be a comma-separated list; the first is the origin.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    return request.client.host if request.client else None


def by(actor) -> dict:
    """Audit kwargs for whoever acts: a user (session) or an API key."""
    from app.models.user import ApiKey

    return {"api_key_id": actor.id} if isinstance(actor, ApiKey) else {"user_id": actor.id}


def record(
    session: Session,
    *,
    action: AuditAction,
    user_id: uuid.UUID | None = None,
    api_key_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    detail: dict | None = None,
    request: Request | None = None,
) -> None:
    """Append an audit entry. Exactly one of user_id / api_key_id must be set
    (DB CHECK enforces it). Caller is responsible for the surrounding commit."""
    session.add(
        AuditLog(
            action=action,
            user_id=user_id,
            api_key_id=api_key_id,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
            ip_address=client_ip(request),
        )
    )
