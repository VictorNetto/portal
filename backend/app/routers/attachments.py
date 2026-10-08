"""Attachment endpoints (SPEC §5.1).

Files are proxied through the API (no direct storage URLs), so every read is
authenticated and audit-logged (D8).
"""

import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import audit
from app.db import get_session
from app.deps import get_current_user, require_roles
from app.models.enums import AuditAction, UserRole
from app.models.user import User
from app.schemas.attachment import AttachmentOut
from app.services import attachment as svc
from app.storage import get_storage

router = APIRouter(tags=["attachments"])

_writer = require_roles(UserRole.admin, UserRole.write_all, UserRole.write_restricted)


@router.get("/vulnerabilities/{vuln_id}/attachments", response_model=list[AttachmentOut])
def list_attachments(
    vuln_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list:
    return svc.list_for_vuln(session, vuln_id, user)


@router.post(
    "/vulnerabilities/{vuln_id}/attachments",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_attachment(
    vuln_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    display_name: str | None = Form(default=None),
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
):
    return svc.add(session, vuln_id, file, display_name, user, request)


@router.get("/reports/{report_id}/attachments", response_model=list[AttachmentOut])
def list_report_attachments(
    report_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list:
    return svc.list_for_report(session, report_id, user)


@router.post(
    "/reports/{report_id}/attachments",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_report_attachment(
    report_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    display_name: str | None = Form(default=None),
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
):
    return svc.add_to_report(session, report_id, file, display_name, user, request)


@router.get("/attachments/{attachment_id}/content")
def attachment_content(
    attachment_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    att = svc.get(session, attachment_id, user)
    audit.record(
        session, action=AuditAction.read, user_id=user.id,
        entity_type="attachment", entity_id=att.id,
        detail={"filename": att.original_filename}, request=request,
    )
    session.commit()

    # Images render inline (markdown embeds); everything else downloads.
    disposition = "inline" if att.is_image else "attachment"
    headers = {
        # Never let a browser sniff a different type than the one we declare.
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, max-age=0, must-revalidate",
        "Content-Length": str(att.size_bytes),
        "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(att.original_filename)}",
    }
    return StreamingResponse(
        get_storage().open(att.s3_key), media_type=att.mime_type, headers=headers
    )


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: uuid.UUID,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
) -> None:
    svc.remove(session, attachment_id, user, request)
