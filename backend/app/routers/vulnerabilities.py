"""Standalone vulnerability endpoints (SPEC §5, §8)."""

import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.vulnerability import VulnCreate, VulnListItem, VulnOut, VulnUpdate
from app.services import vulnerability as svc

router = APIRouter(prefix="/vulnerabilities", tags=["vulnerabilities"])

# Writers and admins may mutate; everyone authenticated may read.
_writer = require_roles(UserRole.admin, UserRole.writer_all)


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
    return svc.get_standalone(session, vuln_id)


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


@router.delete("/{vuln_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vuln(
    vuln_id: uuid.UUID,
    request: Request,
    user: User = Depends(_writer),
    session: Session = Depends(get_session),
) -> None:
    svc.soft_delete(session, vuln_id, user, request)
