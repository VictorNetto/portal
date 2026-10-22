"""Report template rules.

Templates only matter to people who create reports: other roles get 403 everywhere here.
Among those, a template is seen by its owner, by everyone when it is global, and by admins
(all of them). Only an admin makes a template global.
"""

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import access, audit
from app.models.enums import AuditAction, UserRole
from app.models.report_template import ReportTemplate
from app.models.user import User
from app.schemas.report_template import (
    TemplateCreate,
    TemplateListItem,
    TemplateOut,
    TemplateSection,
    TemplateUpdate,
)
from app.schemas.vulnerability import OperatorRef


def _can_see(user: User, tpl: ReportTemplate) -> bool:
    return user.role == UserRole.admin or tpl.is_global or tpl.owner_id == user.id


def _require_creator(user: User) -> None:
    if not access.can_create(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, access.FORBIDDEN)


def get_visible(session: Session, template_id: uuid.UUID, user: User) -> ReportTemplate:
    """A template the user may see; 404 otherwise (its existence is not revealed)."""
    _require_creator(user)
    tpl = session.get(ReportTemplate, template_id)
    if tpl is None or not _can_see(user, tpl):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    return tpl


def _item(tpl: ReportTemplate, user: User) -> dict:
    return dict(
        id=tpl.id, name=tpl.name, is_global=tpl.is_global,
        owner=OperatorRef.model_validate(tpl.owner), mine=tpl.owner_id == user.id,
        section_count=len(tpl.sections or []),
        created_at=tpl.created_at, updated_at=tpl.updated_at,
    )


def to_out(tpl: ReportTemplate, user: User) -> TemplateOut:
    return TemplateOut(
        **_item(tpl, user),
        executive_summary_md=tpl.executive_summary_md,
        introduction_md=tpl.introduction_md,
        sections=[TemplateSection(**s) for s in tpl.sections or []],
    )


def list_templates(session: Session, user: User) -> list[TemplateListItem]:
    _require_creator(user)
    stmt = select(ReportTemplate).order_by(ReportTemplate.name)
    if user.role != UserRole.admin:
        stmt = stmt.where(or_(ReportTemplate.owner_id == user.id, ReportTemplate.is_global.is_(True)))
    return [TemplateListItem(**_item(t, user)) for t in session.scalars(stmt)]


def create(session: Session, body: TemplateCreate, user: User, request: Request) -> TemplateOut:
    _require_creator(user)
    if body.is_global and user.role != UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an admin can make a template available to everyone")
    name = body.name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "name cannot be empty")
    tpl = ReportTemplate(
        name=name, owner_id=user.id, is_global=body.is_global,
        executive_summary_md=body.executive_summary_md,
        introduction_md=body.introduction_md,
        sections=[
            {"title": s.title.strip(), "content_markdown": s.content_markdown}
            for s in body.sections if s.title.strip()
        ],
    )
    session.add(tpl)
    session.flush()
    audit.record(
        session, action=AuditAction.create, user_id=user.id,
        entity_type="report_template", entity_id=tpl.id,
        detail={"name": name, "is_global": body.is_global}, request=request,
    )
    session.commit()
    session.refresh(tpl)
    return to_out(tpl, user)


def update(
    session: Session, template_id: uuid.UUID, body: TemplateUpdate, admin: User, request: Request
) -> TemplateOut:
    tpl = get_visible(session, template_id, admin)
    if tpl.is_global != body.is_global:
        audit.record(
            session, action=AuditAction.update, user_id=admin.id,
            entity_type="report_template", entity_id=tpl.id,
            detail={"is_global": {"from": tpl.is_global, "to": body.is_global}}, request=request,
        )
        tpl.is_global = body.is_global
    session.commit()
    session.refresh(tpl)
    return to_out(tpl, admin)
