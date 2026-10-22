"""Report template endpoints."""

import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.report_template import (
    TemplateCreate,
    TemplateListItem,
    TemplateOut,
    TemplateUpdate,
)
from app.services import report_template as svc

router = APIRouter(prefix="/report-templates", tags=["report-templates"])

_admin = require_roles(UserRole.admin)


@router.get("", response_model=list[TemplateListItem])
def list_templates(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list:
    return svc.list_templates(session, user)


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(
    body: TemplateCreate,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TemplateOut:
    return svc.create(session, body, user, request)


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(
    template_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TemplateOut:
    return svc.to_out(svc.get_visible(session, template_id, user), user)


@router.patch("/{template_id}", response_model=TemplateOut)
def update_template(
    template_id: uuid.UUID,
    body: TemplateUpdate,
    request: Request,
    admin: User = Depends(_admin),
    session: Session = Depends(get_session),
) -> TemplateOut:
    return svc.update(session, template_id, body, admin, request)
