"""Audit log viewer (SPEC §10.3). Accessible to auditor and admin.

Read-access to the audit log is itself NOT re-logged here (it would recurse and
flood); D8's read-logging applies to records, not to viewing the audit trail.

The page's filter bar uses the Hub's grammar; the browser parses it into the tokens of
`AuditSearch` (dates already as UTC instants) and the filtering happens here, in SQL,
because the log is paginated on the server.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, false, func, or_, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import require_roles
from app.models.attachment import Attachment
from app.models.audit import AuditLog
from app.models.dashboard import Dashboard, DashboardLink
from app.models.enums import AuditAction, UserRole
from app.models.report import Report
from app.models.report_template import ReportTemplate
from app.models.user import ApiKey, User
from app.models.vulnerability import Vulnerability
from app.schemas.audit import AuditEntry, AuditFacets, AuditFilter, AuditPage, AuditSearch

router = APIRouter(prefix="/audit-logs", tags=["audit"])
_auditor = require_roles(UserRole.admin, UserRole.auditor)

A = AuditLog


def _like(text: str) -> str:
    esc = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{esc}%"


def _sure(cond):
    """NULL counts as "no": so that a negated filter keeps the rows it does not match."""
    return func.coalesce(cond, false())


def _actor_cond(text: str):
    """Who did it: a user (login, display or full name), an API key ("api:<prefix>" or its
    label), the name typed on a failed login, or "system"."""
    t = text.strip()
    pat = _like(t)
    users = select(User.id).where(or_(
        User.username.ilike(pat), User.display_name.ilike(pat), User.full_name.ilike(pat)))
    key_text = t[4:] if t.lower().startswith("api:") else t
    keys = select(ApiKey.id).where(or_(ApiKey.key_prefix.ilike(_like(key_text)), ApiKey.label.ilike(pat)))
    conds = [
        A.user_id.in_(users),
        A.api_key_id.in_(keys),
        (A.action == AuditAction.login_failed) & A.detail["username"].astext.ilike(pat),
    ]
    if "system".startswith(t.lower()) or t.lower() in "system":
        conds.append(A.user_id.is_(None) & A.api_key_id.is_(None) & (A.action != AuditAction.login_failed))
    return or_(*conds)


def _record_ids(text: str, exact: bool):
    """Ids of the vulnerabilities / reports whose internal id is (or contains) `text`."""
    t = text.strip()
    match = (lambda col: func.lower(col) == t.lower()) if exact else (lambda col: col.ilike(_like(t)))
    return (select(Vulnerability.id).where(match(Vulnerability.internal_id))
            .union(select(Report.id).where(match(Report.internal_id))))


def _record_cond(text: str):
    """The record itself (a VULN/report internal id, or any entity's uuid) and its attachments."""
    t = text.strip()
    try:
        ids = [uuid.UUID(t)]
        rec = A.entity_id.in_(ids)
        owners = ids
    except ValueError:
        sub = _record_ids(t, exact=True).subquery()
        rec = A.entity_id.in_(select(sub.c.id))
        owners = select(sub.c.id)
    atts = select(Attachment.id).where(or_(
        Attachment.vulnerability_id.in_(owners), Attachment.report_id.in_(owners)))
    return or_(rec, (A.entity_type == "attachment") & A.entity_id.in_(atts))


def _naive_utc(d: datetime) -> datetime:
    return d.astimezone(UTC).replace(tzinfo=None) if d.tzinfo else d


def _condition(f: AuditFilter):
    if f.key == "action":
        cond = A.action.in_([AuditAction(v) for v in f.values])
    elif f.key == "role":
        cond = A.user_id.in_(select(User.id).where(User.role.in_([UserRole(v) for v in f.values])))
    elif f.key == "entity":
        named = [v for v in f.values if v != "none"]
        parts = [A.entity_type.in_(named)] if named else []
        if "none" in f.values:
            parts.append(A.entity_type.is_(None))
        cond = or_(*parts)
    elif f.key == "date":
        parts = []
        if f.from_:
            parts.append(A.created_at >= _naive_utc(f.from_))
        if f.to:
            parts.append(A.created_at < _naive_utc(f.to))
        cond = parts[0] if len(parts) == 1 else parts[0] & parts[1]
    elif f.key == "actor":
        cond = _actor_cond(f.text)
    elif f.key == "record":
        cond = _record_cond(f.text)
    elif f.key == "ip":
        cond = func.host(A.ip_address).ilike(_like(f.text.strip()))
    elif f.key == "detail":
        cond = cast(A.detail, String).ilike(_like(f.text.strip()))
    else:  # free text: anywhere in the row
        t = f.text.strip()
        pat = _like(t)
        cond = or_(
            _actor_cond(t),
            cast(A.action, String).ilike(pat),
            A.entity_type.ilike(pat),
            cast(A.detail, String).ilike(pat),
            func.host(A.ip_address).ilike(pat),
            A.entity_id.in_(_record_ids(t, exact=False)),
        )
    cond = _sure(cond)
    return ~cond if f.negate else cond


def _labels(session: Session, rows: list[AuditLog]) -> dict:
    """A readable name for each record the page mentions, in one query per kind."""
    by_type: dict[str, set] = {}
    for r in rows:
        if r.entity_type and r.entity_id:
            by_type.setdefault(r.entity_type, set()).add(r.entity_id)
    sources = {
        "vulnerability": (Vulnerability, lambda o: o.internal_id or o.identifier),
        "report": (Report, lambda o: o.internal_id or o.name),
        "user": (User, lambda o: o.username),
        "report_template": (ReportTemplate, lambda o: o.name),
        "dashboard": (Dashboard, lambda o: o.name),
        "dashboard_link": (DashboardLink, lambda o: o.label),
        "api_key": (ApiKey, lambda o: f"{o.label} ({o.key_prefix})"),
        "attachment": (Attachment, lambda o: o.display_name or o.original_filename),
    }
    out = {}
    for kind, ids in by_type.items():
        if kind not in sources:
            continue
        model, label = sources[kind]
        for o in session.scalars(select(model).where(model.id.in_(ids))):
            out[(kind, o.id)] = label(o)
    return out


def _page(session: Session, filters: list[AuditFilter], page: int, page_size: int) -> AuditPage:
    where = [_condition(f) for f in filters]
    total = session.scalar(select(func.count()).select_from(A).where(*where)) or 0
    rows = list(session.scalars(
        select(A).where(*where)
        .order_by(A.created_at.desc(), A.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ))

    # Resolve actor labels in bulk.
    user_ids = {r.user_id for r in rows if r.user_id}
    key_ids = {r.api_key_id for r in rows if r.api_key_id}
    users = {u.id: u for u in session.scalars(select(User).where(User.id.in_(user_ids)))} if user_ids else {}
    key_prefixes = dict(
        session.execute(select(ApiKey.id, ApiKey.key_prefix).where(ApiKey.id.in_(key_ids))).all()
    ) if key_ids else {}
    labels = _labels(session, rows)

    def actor(r: AuditLog) -> tuple[str, str | None]:
        if r.user_id:
            u = users.get(r.user_id)
            if u is None:
                return "unknown-user", None
            return u.username, (u.shown_name if u.shown_name != u.username else None)
        if r.api_key_id:
            return f"api:{key_prefixes.get(r.api_key_id, '????')}", None
        if r.action == AuditAction.login_failed:
            return (r.detail or {}).get("username") or "unknown-user", None
        return "system", None

    items = []
    for r in rows:
        who, name = actor(r)
        items.append(AuditEntry(
            id=r.id, actor=who, actor_name=name, action=r.action,
            entity_type=r.entity_type, entity_id=r.entity_id,
            entity_label=labels.get((r.entity_type, r.entity_id)),
            detail=r.detail, ip_address=str(r.ip_address) if r.ip_address else None,
            created_at=r.created_at,
        ))
    return AuditPage(items=items, total=total, page=page, page_size=page_size)


@router.get("", response_model=AuditPage)
def list_audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    action: AuditAction | None = None,
    entity_type: str | None = None,
    _: User = Depends(_auditor),
    session: Session = Depends(get_session),
) -> AuditPage:
    filters = []
    if action is not None:
        filters.append(AuditFilter(key="action", values=[action.value]))
    if entity_type:
        filters.append(AuditFilter(key="entity", values=[entity_type]))
    return _page(session, filters, page, page_size)


@router.post("/search", response_model=AuditPage)
def search_audit(
    body: AuditSearch,
    _: User = Depends(_auditor),
    session: Session = Depends(get_session),
) -> AuditPage:
    """The audit page's filter bar: every token must match (AND)."""
    return _page(session, body.filters, body.page, body.page_size)


@router.get("/facets", response_model=AuditFacets)
def audit_facets(
    _: User = Depends(_auditor),
    session: Session = Depends(get_session),
) -> AuditFacets:
    """Values for the filter menus: the active users' logins (plus "system") and the kinds
    of record the log mentions."""
    actors = list(session.scalars(select(User.username).where(User.is_active.is_(True)).order_by(User.username)))
    types = list(session.scalars(
        select(A.entity_type).where(A.entity_type.is_not(None)).distinct().order_by(A.entity_type)))
    return AuditFacets(actors=[*actors, "system"], entity_types=[*types, "none"])
