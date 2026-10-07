"""Standalone vulnerability endpoints (SPEC §5, §8)."""

import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.vulnerability import (
    CorrectionRequest,
    RvsSet,
    TransitionRequest,
    VulnCreate,
    VulnListItem,
    VulnOut,
    VulnUpdate,
)
from app.services import vulnerability as svc

router = APIRouter(prefix="/vulnerabilities", tags=["vulnerabilities"])

# A separate router for the RVS queue (its own top-level path).
rvs_router = APIRouter(prefix="/rvs-queue", tags=["rvs"])

# Writers and admins may mutate; everyone authenticated may read.
_writer = require_roles(UserRole.admin, UserRole.writer_all)
_admin = require_roles(UserRole.admin)


@rvs_router.get("", response_model=list[VulnOut])
def rvs_queue(
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list:
    return svc.rvs_queue(session)


@router.get("", response_model=list[VulnListItem])
def list_vulns(
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list:
    return svc.list_standalone(session)


@router.post("", response_model=VulnOut, status_code=status.HTTP_201_CREATED)
def create_vuln(
    body: VulnCreate,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
) -> VulnOut:
    return svc.create(session, body, user, request)


@router.get("/{vuln_id}", response_model=VulnOut)
def get_vuln(
    vuln_id: uuid.UUID,
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> VulnOut:
    return svc.get_visible(session, vuln_id)


@router.patch("/{vuln_id}", response_model=VulnOut)
def update_vuln(
    vuln_id: uuid.UUID,
    body: VulnUpdate,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
) -> VulnOut:
    return svc.update(session, vuln_id, body, user, request)


@router.post("/{vuln_id}/send", response_model=VulnOut)
def send_vuln(
    vuln_id: uuid.UUID,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
) -> VulnOut:
    return svc.send(session, vuln_id, user, request)


@router.post("/{vuln_id}/dispatch", response_model=VulnOut)
def dispatch_vuln(
    vuln_id: uuid.UUID,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
) -> VulnOut:
    return svc.dispatch_vuln(session, vuln_id, user, request)


@router.post("/{vuln_id}/rvs", response_model=VulnOut)
def set_rvs(
    vuln_id: uuid.UUID,
    body: RvsSet,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
) -> VulnOut:
    return svc.set_rvs(session, vuln_id, body.rvs_id, user, request)


@router.post("/{vuln_id}/transition", response_model=VulnOut)
def transition_vuln(
    vuln_id: uuid.UUID,
    body: TransitionRequest,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
) -> VulnOut:
    return svc.transition(session, vuln_id, body.to, user, request)


@router.post("/{vuln_id}/correction", response_model=VulnOut)
def correct_vuln(
    vuln_id: uuid.UUID,
    body: CorrectionRequest,
    request: Request,
    user: User = Depends(_admin),
    session: Session = Depends(get_session),
) -> VulnOut:
    return svc.correct(session, vuln_id, body.to, body.reason, user, request)


@router.delete("/{vuln_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vuln(
    vuln_id: uuid.UUID,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
) -> None:
    svc.soft_delete(session, vuln_id, user, request)
