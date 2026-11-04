"""The defense team's endpoints (D17). The only routes a defense account can reach."""

import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import audit
from app.db import get_session
from app.deps import get_defense_user
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.defense import (
    DefenseAttachment,
    DefenseRiskAccept,
    DefenseRvs,
    DefenseVuln,
    DefenseVulnItem,
)
from app.services import defense as svc
from app.storage import get_storage

router = APIRouter(prefix="/defense", tags=["defense"])


@router.get("/vulnerabilities", response_model=list[DefenseVulnItem])
def list_vulns(
    _: User = Depends(get_defense_user),
    session: Session = Depends(get_session),
) -> list:
    return svc.list_vulns(session)


@router.get("/vulnerabilities/{vuln_id}", response_model=DefenseVuln)
def get_vuln(
    vuln_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_defense_user),
    session: Session = Depends(get_session),
):
    vuln = svc.get_vuln(session, vuln_id)
    audit.record(
        session, action=AuditAction.read, user_id=user.id,
        entity_type="vulnerability", entity_id=vuln.id, request=request,
    )
    session.commit()
    return vuln


@router.post("/vulnerabilities/{vuln_id}/accept", response_model=DefenseVuln)
def accept(
    vuln_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_defense_user),
    session: Session = Depends(get_session),
):
    return svc.accept(session, vuln_id, user, request)


@router.post("/vulnerabilities/{vuln_id}/risk-accept", response_model=DefenseVuln)
def accept_risk(
    vuln_id: uuid.UUID,
    body: DefenseRiskAccept,
    request: Request,
    user: User = Depends(get_defense_user),
    session: Session = Depends(get_session),
):
    return svc.accept_risk(session, vuln_id, body.reason, user, request)


@router.post("/vulnerabilities/{vuln_id}/rvs", response_model=DefenseVuln)
def set_rvs(
    vuln_id: uuid.UUID,
    body: DefenseRvs,
    request: Request,
    user: User = Depends(get_defense_user),
    session: Session = Depends(get_session),
):
    return svc.set_rvs(session, vuln_id, body.rvs_id, user, request)


@router.get("/vulnerabilities/{vuln_id}/attachments", response_model=list[DefenseAttachment])
def list_attachments(
    vuln_id: uuid.UUID,
    _: User = Depends(get_defense_user),
    session: Session = Depends(get_session),
) -> list:
    return svc.attachments(session, vuln_id)


@router.get("/attachments/{attachment_id}/content")
def attachment_content(
    attachment_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_defense_user),
    session: Session = Depends(get_session),
):
    att = svc.attachment(session, attachment_id)
    audit.record(
        session, action=AuditAction.read, user_id=user.id,
        entity_type="attachment", entity_id=att.id,
        detail={"filename": att.original_filename}, request=request,
    )
    session.commit()
    # Same headers as the red team's download (routers/attachments.py).
    disposition = "inline" if att.is_image else "attachment"
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, max-age=0, must-revalidate",
        "Content-Length": str(att.size_bytes),
        "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(att.original_filename)}",
    }
    return StreamingResponse(get_storage().open(att.s3_key), media_type=att.mime_type, headers=headers)
