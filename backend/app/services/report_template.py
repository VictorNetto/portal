"""Report template rules.

Templates only matter to people who create reports: other roles get 403 everywhere here.
Among those:
- a template is seen by its owner, by everyone when it is global, and by admins (all of them);
- only an admin makes a template global (or stops sharing it);
- editing and deleting: the owner, while the template is private; admins, always. Once a
  template is shared with everyone it changes only through an admin (D11, option B), so a
  template others rely on cannot change or disappear behind their backs.
Reports created from a template keep their own copy of the text, whatever happens to it.
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

_CONTENT = ("name", "executive_summary_md", "introduction_md", "sections")


def _can_see(user: User, tpl: ReportTemplate) -> bool:
    return user.role == UserRole.admin or tpl.is_global or tpl.owner_id == user.id


def can_edit(user: User, tpl: ReportTemplate) -> bool:
    return user.role == UserRole.admin or (tpl.owner_id == user.id and not tpl.is_global)


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


def _get_editable(session: Session, template_id: uuid.UUID, user: User) -> ReportTemplate:
    tpl = get_visible(session, template_id, user)
    if not can_edit(user, tpl):
        detail = (
            "A template shared with everyone can only be changed by an admin"
            if tpl.is_global else access.FORBIDDEN
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail)
    return tpl


def _item(tpl: ReportTemplate, user: User) -> dict:
    return dict(
        id=tpl.id, name=tpl.name, is_global=tpl.is_global,
        owner=OperatorRef.model_validate(tpl.owner), mine=tpl.owner_id == user.id,
        can_edit=can_edit(user, tpl), version=tpl.version,
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


def _clean_sections(sections: list[TemplateSection]) -> list[dict]:
    return [
        {"title": s.title.strip(), "content_markdown": s.content_markdown}
        for s in sections if s.title.strip()
    ]


def _clean_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "name cannot be empty")
    return name


def create(session: Session, body: TemplateCreate, user: User, request: Request) -> TemplateOut:
    _require_creator(user)
    if body.is_global and user.role != UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an admin can make a template available to everyone")
    name = _clean_name(body.name)
    tpl = ReportTemplate(
        name=name, owner_id=user.id, is_global=body.is_global,
        executive_summary_md=body.executive_summary_md,
        introduction_md=body.introduction_md,
        sections=_clean_sections(body.sections),
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
    session: Session, template_id: uuid.UUID, body: TemplateUpdate, user: User, request: Request
) -> TemplateOut:
    changes = body.model_dump(exclude_unset=True, exclude={"version"})
    content = {k: v for k, v in changes.items() if k in _CONTENT}
    sharing = "is_global" in changes

    if sharing and user.role != UserRole.admin:
        get_visible(session, template_id, user)  # 404 first for templates it cannot see
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an admin can share or unshare a template")
    if content:
        # Lock the row first, so two simultaneous saves cannot both pass the version check.
        _require_creator(user)
        session.execute(
            select(ReportTemplate.id).where(ReportTemplate.id == template_id).with_for_update()
        )
        tpl = _get_editable(session, template_id, user)
    else:
        tpl = get_visible(session, template_id, user)

    if content:
        if body.version is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "version is required to edit a template")
        if body.version != tpl.version:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Version conflict: you have v{body.version}, current is v{tpl.version}. "
                "Reload and reapply your changes.",
            )
        if "name" in content:
            tpl.name = _clean_name(content["name"])
        if "executive_summary_md" in content:
            tpl.executive_summary_md = content["executive_summary_md"]
        if "introduction_md" in content:
            tpl.introduction_md = content["introduction_md"]
        if "sections" in content:
            tpl.sections = _clean_sections(body.sections or [])
        tpl.version += 1
        audit.record(
            session, action=AuditAction.update, user_id=user.id,
            entity_type="report_template", entity_id=tpl.id,
            detail={"fields": sorted(content)}, request=request,
        )

    if sharing and tpl.is_global != body.is_global:
        audit.record(
            session, action=AuditAction.update, user_id=user.id,
            entity_type="report_template", entity_id=tpl.id,
            detail={"is_global": {"from": tpl.is_global, "to": body.is_global}}, request=request,
        )
        tpl.is_global = body.is_global

    session.commit()
    session.refresh(tpl)
    return to_out(tpl, user)


def delete(session: Session, template_id: uuid.UUID, user: User, request: Request) -> None:
    """Remove a template. Reports created from it keep their text (their link is cleared)."""
    tpl = _get_editable(session, template_id, user)
    audit.record(
        session, action=AuditAction.delete, user_id=user.id,
        entity_type="report_template", entity_id=tpl.id,
        detail={"name": tpl.name, "owner": tpl.owner.username, "is_global": tpl.is_global},
        request=request,
    )
    session.delete(tpl)
    session.commit()
