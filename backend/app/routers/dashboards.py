"""Dashboards and TV links (D18, docs/specs/DASHBOARDS.md).

Admins and dashboard accounts build dashboards: each chart is one line of the query language
(services/dashboard_query.py), with the dashboard's variables. Results are aggregates only.
A TV link shows a dashboard without signing in: it is read-only, revocable, audited, and
accepts only the groupings status, severity and source.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.db import get_session
from app.deps import get_dashboard_user
from app.models.dashboard import Dashboard, DashboardLink
from app.models.enums import AuditAction, UserRole
from app.models.user import User
from app.services.dashboard_engine import evaluate, load_rows, local_now
from app.services.dashboard_query import QueryError, check_tv, clean_variables, parse

router = APIRouter(prefix="/dashboards", tags=["dashboards"])
tv_router = APIRouter(prefix="/tv", tags=["dashboards"])

MAX_CHARTS = 24     # over all screens
MAX_SCREENS = 10


class Variable(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    value: str = Field(default="", max_length=200)


class Chart(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    width: int = Field(default=1, ge=1, le=3)


class Screen(BaseModel):
    title: str | None = Field(default=None, max_length=80)
    charts: list[Chart] = Field(default_factory=list, max_length=MAX_CHARTS)


# Data: every 30 s to 1 h. A TV screen: 5 s to 10 min.
Refresh = Field(default=60, ge=30, le=3600)
Rotate = Field(default=30, ge=5, le=600)


class DashboardIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    variables: list[Variable] = Field(default_factory=list, max_length=20)
    screens: list[Screen] = Field(default_factory=lambda: [Screen()], min_length=1, max_length=MAX_SCREENS)
    refresh_seconds: int = Refresh
    rotate_seconds: int = Rotate


class DashboardPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    variables: list[Variable] | None = Field(default=None, max_length=20)
    screens: list[Screen] | None = Field(default=None, min_length=1, max_length=MAX_SCREENS)
    refresh_seconds: int | None = Field(default=None, ge=30, le=3600)
    rotate_seconds: int | None = Field(default=None, ge=5, le=600)


class RunIn(BaseModel):
    # Values the viewer typed for this view only; the saved ones fill the rest.
    variables: list[Variable] | None = None


class PreviewIn(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    variables: list[Variable] = Field(default_factory=list, max_length=20)


class LinkIn(BaseModel):
    label: str = Field(min_length=1, max_length=120)


def _vars(items) -> dict[str, str]:
    try:
        return clean_variables([i if isinstance(i, dict) else i.model_dump() for i in items or []])
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from None


def _names(session: Session, ids) -> dict:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return dict(session.execute(select(User.id, User.username).where(User.id.in_(ids))).all())


def _out(d: Dashboard, names: dict) -> dict:
    return {
        "id": str(d.id), "name": d.name, "description": d.description,
        "variables": d.variables, "screens": d.screens,
        "refresh_seconds": d.refresh_seconds, "rotate_seconds": d.rotate_seconds,
        "created_by": names.get(d.created_by), "updated_by": names.get(d.updated_by),
        "created_at": d.created_at.isoformat(), "updated_at": d.updated_at.isoformat(),
    }


def _charts(screens: list[dict]):
    """(screen index, chart index, chart) over every screen."""
    for s, screen in enumerate(screens):
        for i, c in enumerate(screen.get("charts", [])):
            yield s, i, c


def _screens(items: list[Screen]) -> list[dict]:
    out = [{"title": (s.title or "").strip() or None, "charts": [c.model_dump() for c in s.charts]} for s in items]
    if sum(len(s["charts"]) for s in out) > MAX_CHARTS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"At most {MAX_CHARTS} charts in a dashboard")
    return out


def _validate(screens: list[dict], variables: dict, now: datetime) -> None:
    """Every chart must parse with the dashboard's variables: a saved chart that can't run
    would only show an error on the screen (or the TV)."""
    errors = []
    for s, i, c in _charts(screens):
        try:
            parse(c["query"], variables, now)
        except QueryError as e:
            errors.append({"screen": s, "chart": i, **e.as_dict()})
    if errors:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, {"code": "invalid_charts", "errors": errors})


def _get(session: Session, dashboard_id: uuid.UUID) -> Dashboard:
    d = session.get(Dashboard, dashboard_id)
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dashboard not found")
    return d


def _run(screens: list[dict], variables: dict, rows: list[dict], now: datetime, tv: bool = False) -> list[dict]:
    out = []
    for screen in screens:
        charts = []
        for c in screen.get("charts", []):
            item = {"width": c.get("width", 1)}
            try:
                q = parse(c["query"], variables, now)
                if tv:
                    check_tv(q)
                item["result"] = evaluate(q, rows, now)
            except QueryError as e:
                # a TV never shows why a chart failed
                item["error"] = {"code": "unavailable", "pos": 0, "params": {}} if tv else e.as_dict()
            charts.append(item)
        out.append({"title": screen.get("title"), "charts": charts})
    return out


# --- dashboards ---------------------------------------------------------------------------

@router.get("")
def list_dashboards(_: User = Depends(get_dashboard_user), session: Session = Depends(get_session)) -> list:
    items = list(session.scalars(select(Dashboard).order_by(Dashboard.name)))
    names = _names(session, [d.created_by for d in items] + [d.updated_by for d in items])
    return [{**_out(d, names), "chart_count": sum(1 for _ in _charts(d.screens)),
             "screen_count": len(d.screens)} for d in items]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_dashboard(body: DashboardIn, request: Request, user: User = Depends(get_dashboard_user),
                     session: Session = Depends(get_session)) -> dict:
    variables = _vars(body.variables)
    screens = _screens(body.screens)
    _validate(screens, variables, local_now())
    d = Dashboard(name=body.name.strip(), description=body.description, created_by=user.id,
                  variables=[v.model_dump() for v in body.variables], screens=screens,
                  refresh_seconds=body.refresh_seconds, rotate_seconds=body.rotate_seconds)
    session.add(d)
    session.flush()
    audit.record(session, action=AuditAction.create, user_id=user.id, entity_type="dashboard",
                 entity_id=d.id, detail={"name": d.name}, request=request)
    session.commit()
    session.refresh(d)
    return _out(d, _names(session, [d.created_by]))


@router.post("/preview")
def preview(body: PreviewIn, _: User = Depends(get_dashboard_user), session: Session = Depends(get_session)):
    """Run one query while it is being written."""
    now = local_now()
    try:
        q = parse(body.query, _vars(body.variables), now)
    except QueryError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, e.as_dict()) from None
    tv_error = None
    try:
        check_tv(q)
    except QueryError as e:
        tv_error = e.as_dict()
    return {"result": evaluate(q, load_rows(session), now), "tv_error": tv_error}


@router.get("/{dashboard_id}")
def get_dashboard(dashboard_id: uuid.UUID, _: User = Depends(get_dashboard_user),
                  session: Session = Depends(get_session)) -> dict:
    d = _get(session, dashboard_id)
    return _out(d, _names(session, [d.created_by, d.updated_by]))


@router.patch("/{dashboard_id}")
def update_dashboard(dashboard_id: uuid.UUID, body: DashboardPatch, request: Request,
                     user: User = Depends(get_dashboard_user), session: Session = Depends(get_session)) -> dict:
    d = _get(session, dashboard_id)
    variables = _vars(body.variables if body.variables is not None else d.variables)
    screens = _screens(body.screens) if body.screens is not None else d.screens
    _validate(screens, variables, local_now())
    changed = []
    if body.name is not None and body.name.strip() != d.name:
        d.name = body.name.strip()
        changed.append("name")
    if "description" in body.model_fields_set and body.description != d.description:
        d.description = body.description
        changed.append("description")
    if body.variables is not None:
        new = [v.model_dump() for v in body.variables]
        if new != d.variables:
            d.variables = new
            changed.append("variables")
    if body.screens is not None and screens != d.screens:
        d.screens = screens
        changed.append("screens")
    for field in ("refresh_seconds", "rotate_seconds"):
        value = getattr(body, field)
        if value is not None and value != getattr(d, field):
            setattr(d, field, value)
            changed.append(field)
    if changed:
        d.updated_by = user.id
        d.updated_at = datetime.now(UTC).replace(tzinfo=None)
        audit.record(session, action=AuditAction.update, user_id=user.id, entity_type="dashboard",
                     entity_id=d.id, detail={"name": d.name, "changed": changed}, request=request)
    session.commit()
    session.refresh(d)
    return _out(d, _names(session, [d.created_by, d.updated_by]))


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard(dashboard_id: uuid.UUID, request: Request, user: User = Depends(get_dashboard_user),
                     session: Session = Depends(get_session)) -> None:
    d = _get(session, dashboard_id)
    audit.record(session, action=AuditAction.delete, user_id=user.id, entity_type="dashboard",
                 entity_id=d.id, detail={"name": d.name}, request=request)
    session.delete(d)  # its TV links go with it (ON DELETE CASCADE)
    session.commit()


@router.post("/{dashboard_id}/run")
def run_dashboard(dashboard_id: uuid.UUID, body: RunIn | None = None, _: User = Depends(get_dashboard_user),
                  session: Session = Depends(get_session)) -> dict:
    d = _get(session, dashboard_id)
    variables = _vars(d.variables)
    if body and body.variables:
        variables.update(_vars(body.variables))
    now = local_now()
    return {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "screens": _run(d.screens, variables, load_rows(session), now)}


# --- TV links -----------------------------------------------------------------------------

def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _link_out(link: DashboardLink, names: dict) -> dict:
    return {"id": str(link.id), "label": link.label, "created_by": names.get(link.created_by),
            "created_at": link.created_at.isoformat(),
            "revoked_at": link.revoked_at.isoformat() if link.revoked_at else None,
            "last_used_at": link.last_used_at.isoformat() if link.last_used_at else None}


@router.get("/{dashboard_id}/links")
def list_links(dashboard_id: uuid.UUID, _: User = Depends(get_dashboard_user),
               session: Session = Depends(get_session)) -> list:
    _get(session, dashboard_id)
    links = list(session.scalars(select(DashboardLink).where(DashboardLink.dashboard_id == dashboard_id)
                                 .order_by(DashboardLink.created_at.desc())))
    names = _names(session, [link.created_by for link in links])
    return [_link_out(link, names) for link in links]


@router.post("/{dashboard_id}/links", status_code=status.HTTP_201_CREATED)
def create_link(dashboard_id: uuid.UUID, body: LinkIn, request: Request, user: User = Depends(get_dashboard_user),
                session: Session = Depends(get_session)) -> dict:
    d = _get(session, dashboard_id)
    variables, now = _vars(d.variables), local_now()
    errors = []
    for s, i, c in _charts(d.screens):
        try:
            check_tv(parse(c["query"], variables, now))
        except QueryError as e:
            errors.append({"screen": s, "chart": i, **e.as_dict()})
    if errors:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, {"code": "not_for_tv", "errors": errors})
    token = secrets.token_urlsafe(32)
    link = DashboardLink(dashboard_id=d.id, label=body.label.strip(), token_hash=_hash(token), created_by=user.id)
    session.add(link)
    session.flush()
    audit.record(session, action=AuditAction.create, user_id=user.id, entity_type="dashboard_link",
                 entity_id=link.id, detail={"dashboard": d.name, "label": link.label}, request=request)
    session.commit()
    session.refresh(link)
    # The token is shown this once; only its hash is kept.
    return {**_link_out(link, _names(session, [user.id])), "token": token}


@router.post("/{dashboard_id}/links/{link_id}/revoke")
def revoke_link(dashboard_id: uuid.UUID, link_id: uuid.UUID, request: Request,
                user: User = Depends(get_dashboard_user), session: Session = Depends(get_session)) -> dict:
    link = session.get(DashboardLink, link_id)
    if link is None or link.dashboard_id != dashboard_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link not found")
    if link.revoked_at is None:
        link.revoked_at = datetime.now(UTC).replace(tzinfo=None)
        audit.record(session, action=AuditAction.update, user_id=user.id, entity_type="dashboard_link",
                     entity_id=link.id, detail={"label": link.label, "revoked": True}, request=request)
        session.commit()
        session.refresh(link)
    return _link_out(link, _names(session, [link.created_by]))


@tv_router.get("/{token}")
def tv(token: str, session: Session = Depends(get_session)) -> dict:
    """A TV board, without signing in. One answer for every failure, so it reveals nothing."""
    gone = HTTPException(status.HTTP_404_NOT_FOUND, "Link not found")
    if len(token) > 100:
        raise gone
    link = session.scalar(select(DashboardLink).where(DashboardLink.token_hash == _hash(token)))
    if link is None or link.revoked_at is not None:
        raise gone
    # It computes with the access of whoever made it: if that account can't, neither can the TV.
    maker = session.get(User, link.created_by)
    if maker is None or not maker.is_active or maker.role not in (UserRole.admin, UserRole.dashboard):
        raise gone
    d = session.get(Dashboard, link.dashboard_id)
    link.last_used_at = datetime.now(UTC).replace(tzinfo=None)
    session.commit()
    now = local_now()
    return {"name": d.name, "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "refresh_seconds": d.refresh_seconds, "rotate_seconds": d.rotate_seconds,
            "screens": _run(d.screens, _vars(d.variables), load_rows(session), now, tv=True)}
