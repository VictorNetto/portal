"""What the defense team may do (D17).

A defense account sees only vulnerabilities that were sent to it: status sent or later,
never a draft, a ready vuln or anything inside a draft report. It accepts a sent vuln and
then records its RVS ID, which moves it to fixing; or it assumes the risk instead
(risk_accepted). Reports, internal notes, operators and sharing are the red team's and
are never shown.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.models.attachment import Attachment
from app.models.enums import AuditAction, VulnStatus
from app.models.user import User
from app.models.vulnerability import Vulnerability
from app.services import vulnerability as vuln_svc

RELEASED = (VulnStatus.sent, VulnStatus.fixing, VulnStatus.retesting, VulnStatus.fixed,
            VulnStatus.risk_accepted)


def _released():
    return Vulnerability.deleted_at.is_(None), Vulnerability.status.in_(RELEASED)


def list_vulns(session: Session) -> list[Vulnerability]:
    return list(session.scalars(
        select(Vulnerability).where(*_released()).order_by(Vulnerability.sent_at.desc())))


def get_vuln(session: Session, vuln_id: uuid.UUID, *, for_update: bool = False) -> Vulnerability:
    stmt = select(Vulnerability).where(Vulnerability.id == vuln_id, *_released())
    vuln = session.scalar(stmt.with_for_update() if for_update else stmt)
    if vuln is None:  # unsent or unknown alike: nothing reveals that it exists
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vulnerability not found")
    return vuln


def attachments(session: Session, vuln_id: uuid.UUID) -> list[Attachment]:
    get_vuln(session, vuln_id)
    return list(session.scalars(
        select(Attachment).where(Attachment.vulnerability_id == vuln_id).order_by(Attachment.created_at)))


def attachment(session: Session, attachment_id: uuid.UUID) -> Attachment:
    """A file of a sent vuln. Report files stay with the red team."""
    att = session.get(Attachment, attachment_id)
    if att is None or att.vulnerability_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attachment not found")
    try:
        get_vuln(session, att.vulnerability_id)
    except HTTPException:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attachment not found") from None
    return att


def accept(session: Session, vuln_id: uuid.UUID, user: User, request: Request) -> Vulnerability:
    vuln = get_vuln(session, vuln_id, for_update=True)
    if vuln.status != VulnStatus.sent:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Only a sent vuln can be accepted (current: {vuln.status.value})")
    if vuln.accepted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already accepted")
    vuln.accepted_at = datetime.now(UTC)
    vuln.accepted_by = user.id
    vuln.version += 1
    audit.record(
        session, action=AuditAction.accept, user_id=user.id,
        entity_type="vulnerability", entity_id=vuln.id, request=request,
    )
    session.commit()
    session.refresh(vuln)
    return vuln


def accept_risk(session: Session, vuln_id: uuid.UUID, reason: str, user: User, request: Request) -> Vulnerability:
    """sent -> risk_accepted: the team will not fix it, and says why. Accepted or not."""
    vuln = get_vuln(session, vuln_id, for_update=True)
    if vuln.status != VulnStatus.sent:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Only a sent vuln can have its risk accepted (current: {vuln.status.value})")
    vuln.status = VulnStatus.risk_accepted
    vuln.risk_accepted_at = datetime.now(UTC)
    vuln.risk_accepted_by = user.id
    vuln.risk_reason = reason.strip()
    vuln.version += 1
    audit.record(
        session, action=AuditAction.status_change, user_id=user.id,
        entity_type="vulnerability", entity_id=vuln.id,
        detail={"from": "sent", "to": "risk_accepted", "reason": vuln.risk_reason}, request=request,
    )
    session.commit()
    session.refresh(vuln)
    return vuln


def undo_risk(session: Session, vuln_id: uuid.UUID, user: User, request: Request) -> Vulnerability:
    """risk_accepted -> sent: the team will fix it after all. An acceptance made before stays,
    so the vuln waits for its RVS ID; the old reason is kept in the audit log."""
    vuln = get_vuln(session, vuln_id, for_update=True)
    if vuln.status != VulnStatus.risk_accepted:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Only a risk-accepted vuln can be reopened (current: {vuln.status.value})")
    reason = vuln.risk_reason
    vuln.status = VulnStatus.sent
    vuln.risk_accepted_at = vuln.risk_accepted_by = vuln.risk_reason = None
    vuln.version += 1
    audit.record(
        session, action=AuditAction.status_change, user_id=user.id,
        entity_type="vulnerability", entity_id=vuln.id,
        detail={"from": "risk_accepted", "to": "sent", "previous_reason": reason}, request=request,
    )
    session.commit()
    session.refresh(vuln)
    return vuln


def set_rvs(session: Session, vuln_id: uuid.UUID, rvs_id: str, user: User, request: Request) -> Vulnerability:
    vuln = get_vuln(session, vuln_id, for_update=True)
    if vuln.status == VulnStatus.sent and vuln.accepted_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Accept the vuln before recording its RVS ID")
    return vuln_svc.apply_rvs(session, vuln, rvs_id, user, request)
