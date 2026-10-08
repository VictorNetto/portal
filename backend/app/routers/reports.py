"""Report endpoints (SPEC §3, §6, §7, §9)."""

import uuid

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.report import (
    ReportCreate,
    ReportListItem,
    ReportOut,
    ReportUpdate,
    SectionCreate,
    SectionReorder,
    SectionUpdate,
)
from app.schemas.vulnerability import BatchExport, VulnCreate, VulnOut
from app.services import report as svc
from app.services import report_dispatch

router = APIRouter(prefix="/reports", tags=["reports"])

_writer = require_roles(UserRole.admin, UserRole.write_all, UserRole.write_restricted)
_admin = require_roles(UserRole.admin)


@router.get("", response_model=list[ReportListItem])
def list_reports(
    user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    return svc.list_reports(session, user)


@router.post("/export")
def export_batch(
    body: BatchExport,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Selected reports as a ZIP of PDFs."""
    data, media_type, filename = report_dispatch.export_reports_batch(session, body.ids, user, request)
    return Response(
        content=data, media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                 "X-Content-Type-Options": "nosniff"},
    )


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    body: ReportCreate,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
):
    return svc.create(session, body, user, request)


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return svc.read(session, report_id, user, request)


@router.patch("/{report_id}", response_model=ReportOut)
def update_report(
    report_id: uuid.UUID,
    body: ReportUpdate,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
):
    return svc.update(session, report_id, body, user, request)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: uuid.UUID,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
) -> None:
    svc.delete(session, report_id, user, request)


# --- dispatch & export ---

@router.post("/{report_id}/dispatch", response_model=ReportOut)
def dispatch_report(
    report_id: uuid.UUID,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
):
    """Two-phase dispatch (D2). Calling it again retries a failed delivery."""
    return report_dispatch.dispatch(session, report_id, user, request)


@router.get("/{report_id}/export")
def export_report(
    report_id: uuid.UUID,
    request: Request,
    format: str = Query("pdf", pattern="^(pdf|xlsx|docx)$"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data, media_type, filename = report_dispatch.export_report(
        session, report_id, format, user, request
    )
    return Response(
        content=data, media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                 "X-Content-Type-Options": "nosniff"},
    )


# --- lock ---

@router.post("/{report_id}/lock", response_model=ReportOut)
def acquire_lock(
    report_id: uuid.UUID,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
):
    return svc.acquire_lock(session, report_id, user)


@router.post("/{report_id}/lock/heartbeat", response_model=ReportOut)
def lock_heartbeat(
    report_id: uuid.UUID,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
):
    return svc.heartbeat(session, report_id, user)


@router.delete("/{report_id}/lock", status_code=status.HTTP_204_NO_CONTENT)
def release_lock(
    report_id: uuid.UUID,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
) -> None:
    svc.release_lock(session, report_id, user)


@router.post("/{report_id}/lock/force-release", status_code=status.HTTP_204_NO_CONTENT)
def force_release_lock(
    report_id: uuid.UUID,
    request: Request,
    admin: User = Depends(_admin),
    session: Session = Depends(get_session),
) -> None:
    svc.force_release(session, report_id, admin, request)


# --- sections ---

@router.post("/{report_id}/sections", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def add_section(
    report_id: uuid.UUID,
    body: SectionCreate,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
):
    return svc.add_section(session, report_id, body, user, request)


@router.post("/{report_id}/sections/reorder", response_model=ReportOut)
def reorder_sections(
    report_id: uuid.UUID,
    body: SectionReorder,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
):
    return svc.reorder_sections(session, report_id, body.ids, user, request)


@router.patch("/{report_id}/sections/{section_id}", response_model=ReportOut)
def update_section(
    report_id: uuid.UUID,
    section_id: uuid.UUID,
    body: SectionUpdate,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
):
    return svc.update_section(session, report_id, section_id, body, user, request)


@router.delete("/{report_id}/sections/{section_id}", response_model=ReportOut)
def delete_section(
    report_id: uuid.UUID,
    section_id: uuid.UUID,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
):
    return svc.delete_section(session, report_id, section_id, user, request)


# --- vulnerabilities inside the report ---

@router.post(
    "/{report_id}/vulnerabilities", response_model=VulnOut, status_code=status.HTTP_201_CREATED
)
def create_report_vuln(
    report_id: uuid.UUID,
    body: VulnCreate,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
):
    return svc.create_vuln(session, report_id, body, user, request)
