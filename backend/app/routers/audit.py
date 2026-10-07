"""Audit log viewer (SPEC §10.3). Accessible to auditor and admin.

Read-access to the audit log is itself NOT re-logged here (it would recurse and
flood); D8's read-logging applies to records, not to viewing the audit trail.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import require_roles
from app.models.audit import AuditLog
from app.models.enums import AuditAction, UserRole
from app.models.user import ApiKey, User
from app.schemas.audit import AuditEntry, AuditPage

router = APIRouter(prefix="/audit-logs", tags=["audit"])
_auditor = require_roles(UserRole.admin, UserRole.auditor)


@router.get("", response_model=AuditPage)
def list_audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    action: AuditAction | None = None,
    entity_type: str | None = None,
    _: User = Depends(_auditor),
    session: Session = Depends(get_session),
) -> AuditPage:
    filters = []
    if action is not None:
        filters.append(AuditLog.action == action)
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)

    total = session.scalar(select(func.count()).select_from(AuditLog).where(*filters)) or 0

    rows = list(
        session.scalars(
            select(AuditLog)
            .where(*filters)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )

    # Resolve actor labels in bulk.
    user_ids = {r.user_id for r in rows if r.user_id}
    key_ids = {r.api_key_id for r in rows if r.api_key_id}
    usernames = dict(
        session.execute(select(User.id, User.username).where(User.id.in_(user_ids))).all()
    ) if user_ids else {}
    key_prefixes = dict(
        session.execute(select(ApiKey.id, ApiKey.key_prefix).where(ApiKey.id.in_(key_ids))).all()
    ) if key_ids else {}

    def actor(r: AuditLog) -> str:
        if r.user_id:
            return usernames.get(r.user_id, "unknown-user")
        if r.api_key_id:
            return f"api:{key_prefixes.get(r.api_key_id, '????')}"
        return "system"

    items = [
        AuditEntry(
            id=r.id, actor=actor(r), action=r.action,
            entity_type=r.entity_type, entity_id=r.entity_id,
            detail=r.detail, ip_address=str(r.ip_address) if r.ip_address else None,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return AuditPage(items=items, total=total, page=page, page_size=page_size)
