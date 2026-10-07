"""Inbound vulnerability creation by machine callers (SPEC §11)."""

from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.models.enums import AuditAction, UserRole, VulnStatus
from app.models.user import ApiKey, User
from app.models.vulnerability import Vulnerability
from app.schemas.ingest import IngestVuln
from app.services.vulnerability import _next_vuln_internal_id

# Same fields the UI requires before a vuln can be sent (FRONTEND_SPEC §8.8).
_REQUIRED_FOR_SAVED_LOCAL = ("identifier", "description", "finding_detail", "mitigation")


def _blank(value: str | None) -> bool:
    return not (value or "").strip()


def _resolve_operators(session: Session, usernames: list[str]) -> list[User]:
    if not usernames:
        return []
    wanted = list(dict.fromkeys(u.strip() for u in usernames if u.strip()))
    users = list(session.scalars(select(User).where(User.username.in_(wanted))))
    by_name = {u.username: u for u in users}
    unknown = [n for n in wanted if n not in by_name]
    # Operators must be real, active accounts that are allowed to work on vulns.
    unusable = [
        n for n, u in by_name.items()
        if not u.is_active or u.role not in (UserRole.admin, UserRole.writer_all)
    ]
    if unknown or unusable:
        problems = []
        if unknown:
            problems.append("unknown operator(s): " + ", ".join(unknown))
        if unusable:
            problems.append("operator(s) not active writers: " + ", ".join(unusable))
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "; ".join(problems))
    return [by_name[n] for n in wanted]


def create(
    session: Session, payload: IngestVuln, key: ApiKey, request: Request
) -> Vulnerability:
    if not any(not _blank(getattr(payload, f)) for f in ("identifier", "description", "finding_detail")):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Provide at least one of: identifier, description, finding_detail",
        )
    if payload.status == "saved_local":
        missing = [f for f in _REQUIRED_FOR_SAVED_LOCAL if _blank(getattr(payload, f))]
        if missing:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Required for status 'saved_local': " + ", ".join(missing),
            )

    operators = _resolve_operators(session, payload.operators)
    vuln = Vulnerability(
        status=VulnStatus.draft,
        identifier=payload.identifier,
        cwe=payload.cwe,
        description=payload.description,
        finding_detail=payload.finding_detail,
        mitigation=payload.mitigation,
        references=payload.references,
        cvss_score=payload.cvss_score,
        cvss_vector=payload.cvss_vector,
        source=payload.source,
        internal_notes=payload.internal_notes,
        extra_metadata=payload.combined_metadata(),
        # The record belongs to whoever issued the key; the key itself is the
        # actor in the audit log.
        created_by=key.created_by,
    )
    vuln.operators = operators
    session.add(vuln)
    session.flush()

    audit.record(
        session, action=AuditAction.create, api_key_id=key.id,
        entity_type="vulnerability", entity_id=vuln.id,
        detail={"via": "api", "source": payload.source, "status": payload.status}, request=request,
    )
    if payload.status == "saved_local":
        vuln.status = VulnStatus.saved_local
        vuln.saved_local_at = datetime.now(UTC)
        vuln.internal_id = _next_vuln_internal_id(session)
        vuln.version += 1
        audit.record(
            session, action=AuditAction.status_change, api_key_id=key.id,
            entity_type="vulnerability", entity_id=vuln.id,
            detail={"from": "draft", "to": "saved_local"}, request=request,
        )
    session.commit()
    session.refresh(vuln)
    return vuln
