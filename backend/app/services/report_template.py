"""Report template rules (D11).

Templates only matter to people who create reports: other roles get 403 everywhere here.

Sharing is reviewed (see models/report_template.py for the states):
- only the owner asks to share a template (private -> pending) or withdraws the request;
- only an admin approves (pending -> shared) or rejects (pending -> private);
- an admin may unshare a shared template (-> unshared: nobody can see or use it, its owner
  included) and share it again (-> shared).

Who sees what:
- admins see every template;
- everyone else sees the shared ones plus their own private / pending ones.
Who uses one to start a report: anyone who sees it, unless it is unshared.
Who edits / deletes: the owner while it is private; admins at any time. A pending template
is frozen for its owner (what the admin approves is what gets shared); a shared one can no
longer be changed by its owner, who would create a new template instead.
Reports created from a template keep their own copy of the text, whatever happens to it.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app import access, audit
from app.models.enums import AuditAction, UserRole
from app.models.report_template import ReportTemplate, ShareStatus
from app.models.user import User
from app.schemas.report_template import (
    SharingAction,
    TemplateCreate,
    TemplateListItem,
    TemplateOut,
    TemplateSection,
    TemplateUpdate,
)
from app.schemas.vulnerability import OperatorRef

P, PEND, S, U = ShareStatus.private, ShareStatus.pending, ShareStatus.shared, ShareStatus.unshared

# action -> (who may take it, from status, to status)
_SHARING: dict[str, tuple[str, ShareStatus, ShareStatus]] = {
    "request": ("owner", P, PEND),
    "withdraw": ("owner", PEND, P),
    "approve": ("admin", PEND, S),
    "reject": ("admin", PEND, P),
    "unshare": ("admin", S, U),
    "reshare": ("admin", U, S),
}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _is_admin(user: User) -> bool:
    return user.role == UserRole.admin


def _can_see(user: User, tpl: ReportTemplate) -> bool:
    if _is_admin(user):
        return True
    if tpl.share_status == S:
        return True
    return tpl.owner_id == user.id and tpl.share_status in (P, PEND)


def can_use(user: User, tpl: ReportTemplate) -> bool:
    return _can_see(user, tpl) and tpl.share_status != U


def can_edit(user: User, tpl: ReportTemplate) -> bool:
    return _is_admin(user) or (tpl.owner_id == user.id and tpl.share_status == P)


def _actions(user: User, tpl: ReportTemplate) -> list[str]:
    out = []
    for action, (who, src, _dst) in _SHARING.items():
        if tpl.share_status != src:
            continue
        if (who == "owner" and tpl.owner_id == user.id) or (who == "admin" and _is_admin(user)):
            out.append(action)
    return out


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


def get_usable(session: Session, template_id: uuid.UUID, user: User) -> ReportTemplate:
    """A template the user may start a report from (unshared ones are available to nobody)."""
    tpl = get_visible(session, template_id, user)
    if not can_use(user, tpl):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    return tpl


def _lock(session: Session, template_id: uuid.UUID) -> None:
    """Row-lock first, so two simultaneous changes cannot both pass their checks."""
    session.execute(select(ReportTemplate.id).where(ReportTemplate.id == template_id).with_for_update())


def _get_editable(session: Session, template_id: uuid.UUID, user: User) -> ReportTemplate:
    tpl = get_visible(session, template_id, user)
    if not can_edit(user, tpl):
        reasons = {
            PEND: "The template is waiting for an admin's approval. Withdraw the request to change it.",
            S: "A shared template can no longer be changed by its owner. Create a new template instead.",
        }
        raise HTTPException(status.HTTP_403_FORBIDDEN, reasons.get(tpl.share_status, access.FORBIDDEN))
    return tpl


def _ref(user: User | None) -> OperatorRef | None:
    return OperatorRef.model_validate(user) if user else None


def _item(tpl: ReportTemplate, user: User) -> dict:
    return dict(
        id=tpl.id, name=tpl.name, share_status=tpl.share_status, is_global=tpl.share_status == S,
        owner=_ref(tpl.owner), mine=tpl.owner_id == user.id,
        can_edit=can_edit(user, tpl), can_use=can_use(user, tpl), actions=_actions(user, tpl),
        share_requested_at=tpl.share_requested_at, share_decided_at=tpl.share_decided_at,
        share_decided_by=_ref(tpl.decided_by),
        version=tpl.version, section_count=len(tpl.sections or []),
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
    if not _is_admin(user):
        stmt = stmt.where(or_(
            ReportTemplate.share_status == S,
            and_(ReportTemplate.owner_id == user.id, ReportTemplate.share_status.in_([P, PEND])),
        ))
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
    name = _clean_name(body.name)
    tpl = ReportTemplate(
        name=name, owner_id=user.id, share_status=P,
        executive_summary_md=body.executive_summary_md,
        introduction_md=body.introduction_md,
        sections=_clean_sections(body.sections),
    )
    session.add(tpl)
    session.flush()
    audit.record(
        session, action=AuditAction.create, user_id=user.id,
        entity_type="report_template", entity_id=tpl.id, detail={"name": name}, request=request,
    )
    session.commit()
    session.refresh(tpl)
    return to_out(tpl, user)


def update(
    session: Session, template_id: uuid.UUID, body: TemplateUpdate, user: User, request: Request
) -> TemplateOut:
    _require_creator(user)
    _lock(session, template_id)
    tpl = _get_editable(session, template_id, user)
    content = body.model_dump(exclude_unset=True, exclude={"version"})
    if body.version != tpl.version:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Version conflict: you have v{body.version}, current is v{tpl.version}. "
            "Reload and reapply your changes.",
        )
    if not content:
        return to_out(tpl, user)
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
    session.commit()
    session.refresh(tpl)
    return to_out(tpl, user)


def change_sharing(
    session: Session, template_id: uuid.UUID, action: SharingAction, user: User, request: Request
) -> TemplateOut:
    _require_creator(user)
    _lock(session, template_id)
    tpl = get_visible(session, template_id, user)
    who, src, dst = _SHARING[action]
    if who == "admin" and not _is_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an admin can do this")
    if who == "owner" and tpl.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the template's owner can do this")
    if tpl.share_status != src:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot '{action}' a template that is '{tpl.share_status.value}'",
        )
    previous = tpl.share_status
    tpl.share_status = dst
    if action == "request":
        tpl.share_requested_at = _now()
    elif action == "withdraw":
        tpl.share_requested_at = None
    else:  # an admin's decision
        tpl.share_decided_at = _now()
        tpl.share_decided_by = user.id
    audit.record(
        session, action=AuditAction.update, user_id=user.id,
        entity_type="report_template", entity_id=tpl.id,
        detail={"sharing": action, "from": previous.value, "to": dst.value}, request=request,
    )
    session.commit()
    session.refresh(tpl)
    return to_out(tpl, user)


def delete(session: Session, template_id: uuid.UUID, user: User, request: Request) -> None:
    """Remove a template. Reports created from it keep their text (their link is cleared)."""
    _require_creator(user)
    _lock(session, template_id)
    tpl = _get_editable(session, template_id, user)
    audit.record(
        session, action=AuditAction.delete, user_id=user.id,
        entity_type="report_template", entity_id=tpl.id,
        detail={"name": tpl.name, "owner": tpl.owner.username, "share_status": tpl.share_status.value},
        request=request,
    )
    session.delete(tpl)
    session.commit()
