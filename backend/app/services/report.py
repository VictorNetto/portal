"""Report business rules (SPEC §3, §6, §7, §15.5–15.7; decisions D1, D4).

Reports are edited under a write lock (see report_lock). A draft report owns its
vulnerabilities; deleting the draft removes them too (D1). Once dispatched the
report is immutable except for its internal notes.
"""

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import audit
from app.models.enums import AuditAction, ReportStatus, VulnStatus
from app.models.report import Report, ReportSection
from app.models.user import User
from app.models.vulnerability import Vulnerability
from app.schemas.report import (
    LockInfo,
    ReportCreate,
    ReportListItem,
    ReportOut,
    ReportUpdate,
    SectionCreate,
    SectionOut,
    SectionUpdate,
)
from app.schemas.vulnerability import OperatorRef, VulnCreate, VulnListItem
from app.services import report_lock
from app.services.vulnerability import _resolve_operators

# Pre-filled on creation (SPEC §6/§7); the operator rewrites it.
DEFAULT_EXECUTIVE_SUMMARY = """## Sumário Executivo

### Objetivo
Descreva o objetivo e o contexto do teste.

### Principais resultados
Resuma os achados mais relevantes e o nível de risco geral.

### Recomendações
Liste as ações prioritárias recomendadas.
"""

_DRAFT_FIELDS = {
    "name", "client_name", "start_date", "end_date", "executive_summary_md",
    "introduction_md", "test_type", "demand_origin", "environment", "scope",
    "test_model", "internal_notes", "operators",
}


def _next_report_internal_id(session: Session) -> str:
    n = session.execute(text("SELECT nextval('report_seq')")).scalar_one()
    return f"OP-{n:04d}"


def get_report(session: Session, report_id: uuid.UUID, for_update: bool = False) -> Report:
    stmt = select(Report).where(Report.id == report_id)
    if for_update:
        stmt = stmt.with_for_update()
    report = session.scalar(stmt)
    if report is None or report.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return report


def _vulns_of(session: Session, report: Report) -> list[Vulnerability]:
    vulns = list(
        session.scalars(
            select(Vulnerability).where(
                Vulnerability.report_id == report.id, Vulnerability.deleted_at.is_(None)
            )
        )
    )
    # Highest CVSS first (SPEC §7); unscored last.
    vulns.sort(key=lambda v: (v.cvss_score is None, -(float(v.cvss_score or 0)), v.created_at))
    return vulns


def _lock_info(session: Session, report: Report, user: User) -> LockInfo | None:
    if report.status != ReportStatus.draft or not report_lock.is_active(report):
        return None
    holder = session.get(User, report.lock_user_id)
    if holder is None:
        return None
    return LockInfo(
        holder_id=holder.id,
        holder_username=holder.username,
        acquired_at=report.lock_acquired_at,
        expires_at=report.lock_last_activity_at + report_lock.LOCK_TTL,
        mine=holder.id == user.id,
    )


def _base(session: Session, report: Report, user: User, vulns: list[Vulnerability]) -> dict:
    scored = [float(v.cvss_score) for v in vulns if v.cvss_score is not None]
    return dict(
        id=report.id, internal_id=report.internal_id, name=report.name,
        client_name=report.client_name, status=report.status,
        operators=[OperatorRef.model_validate(o) for o in report.operators],
        vuln_count=len(vulns), max_cvss=max(scored) if scored else None,
        start_date=report.start_date, end_date=report.end_date,
        lock=_lock_info(session, report, user), dispatched_at=report.dispatched_at,
        created_at=report.created_at, updated_at=report.updated_at,
    )


def to_list_item(session: Session, report: Report, user: User) -> ReportListItem:
    return ReportListItem(**_base(session, report, user, _vulns_of(session, report)))


def to_out(session: Session, report: Report, user: User) -> ReportOut:
    vulns = _vulns_of(session, report)
    sections = sorted(report.sections, key=lambda s: s.position)
    return ReportOut(
        **_base(session, report, user, vulns),
        dispatch_error=report.dispatch_error,
        executive_summary_md=report.executive_summary_md,
        introduction_md=report.introduction_md,
        test_type=report.test_type, demand_origin=report.demand_origin,
        environment=report.environment, scope=report.scope, test_model=report.test_model,
        internal_notes=report.internal_notes,
        sections=[SectionOut.model_validate(s) for s in sections],
        vulnerabilities=[VulnListItem.model_validate(v) for v in vulns],
    )


# --- CRUD ------------------------------------------------------------------

def list_reports(session: Session, user: User) -> list[ReportListItem]:
    reports = session.scalars(
        select(Report).where(Report.deleted_at.is_(None)).order_by(Report.updated_at.desc())
    )
    return [to_list_item(session, r, user) for r in reports]


def read(session: Session, report_id: uuid.UUID, user: User, request: Request) -> ReportOut:
    report = get_report(session, report_id)
    # D8: who read which report, and when.
    audit.record(
        session, action=AuditAction.read, user_id=user.id,
        entity_type="report", entity_id=report.id, request=request,
    )
    session.commit()
    return to_out(session, report, user)


def create(session: Session, body: ReportCreate, user: User, request: Request) -> ReportOut:
    now = report_lock.utcnow()
    report = Report(
        name=body.name.strip(),
        client_name=body.client_name,
        start_date=body.start_date,
        end_date=body.end_date,
        status=ReportStatus.draft,
        internal_id=_next_report_internal_id(session),  # assigned on first save
        executive_summary_md=DEFAULT_EXECUTIVE_SUMMARY,
        created_by=user.id,
        # The creator starts out holding the lock, so they can keep writing.
        lock_user_id=user.id, lock_acquired_at=now, lock_last_activity_at=now,
    )
    report.operators = _resolve_operators(session, body.operator_ids)
    session.add(report)
    session.flush()
    audit.record(
        session, action=AuditAction.create, user_id=user.id,
        entity_type="report", entity_id=report.id, request=request,
    )
    session.commit()
    session.refresh(report)
    return to_out(session, report, user)


def update(
    session: Session, report_id: uuid.UUID, body: ReportUpdate, user: User, request: Request
) -> ReportOut:
    report = get_report(session, report_id, for_update=True)
    changes = body.model_dump(exclude_unset=True)
    set_operators = "operator_ids" in changes
    op_ids = changes.pop("operator_ids", None)
    requested = set(changes) | ({"operators"} if set_operators else set())

    if "name" in changes and not (changes["name"] or "").strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "name cannot be empty")

    if report.status == ReportStatus.dispatched:
        # Immutable, except internal notes (no lock needed: single field).
        extra = requested - {"internal_notes"}
        if extra:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "A dispatched report only allows internal_notes: " + ", ".join(sorted(extra)),
            )
    else:
        report_lock.require_editable(report, user)  # 409 if dispatching / no lock

    start = changes.get("start_date", report.start_date)
    end = changes.get("end_date", report.end_date)
    if start and end and end < start:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "end_date must not be before start_date"
        )

    for field, value in changes.items():
        setattr(report, field, value.strip() if field == "name" else value)
    if set_operators:
        report.operators = _resolve_operators(session, op_ids or [])

    audit.record(
        session, action=AuditAction.update, user_id=user.id,
        entity_type="report", entity_id=report.id,
        detail={"fields": sorted(requested)}, request=request,
    )
    session.commit()
    session.refresh(report)
    return to_out(session, report, user)


def delete(session: Session, report_id: uuid.UUID, user: User, request: Request) -> None:
    """D1: only a draft report can be deleted; its (draft) vulns go with it."""
    report = get_report(session, report_id, for_update=True)
    if report.status != ReportStatus.draft:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Only draft reports can be deleted (D1)"
        )
    if report_lock.is_active(report) and not report_lock.held_by(report, user):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "The report is locked by another operator"
        )
    now = report_lock.utcnow()
    vulns = _vulns_of(session, report)
    for v in vulns:
        v.deleted_at = now
    report.deleted_at = now
    report.lock_user_id = None
    audit.record(
        session, action=AuditAction.delete, user_id=user.id,
        entity_type="report", entity_id=report.id,
        detail={"vulns_removed": len(vulns)}, request=request,
    )
    session.commit()


# --- Lock (§3, D4) ---------------------------------------------------------

def acquire_lock(session: Session, report_id: uuid.UUID, user: User) -> ReportOut:
    report = get_report(session, report_id, for_update=True)
    if report.status != ReportStatus.draft:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"A {report.status.value} report is not editable"
        )
    now = report_lock.utcnow()
    if report_lock.is_active(report, now) and report.lock_user_id != user.id:
        holder = session.get(User, report.lock_user_id)
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"The report is locked by {holder.username if holder else 'another operator'} "
            f"until {(report.lock_last_activity_at + report_lock.LOCK_TTL):%H:%M} (UTC) "
            "unless they stop working on it",
        )
    if not report_lock.held_by(report, user, now):
        report.lock_acquired_at = now
    report.lock_user_id = user.id
    report.lock_last_activity_at = now
    session.commit()
    session.refresh(report)
    return to_out(session, report, user)


def heartbeat(session: Session, report_id: uuid.UUID, user: User) -> ReportOut:
    """Keep-alive while the editor is open and the operator is active."""
    report = get_report(session, report_id, for_update=True)
    report_lock.require_editable(report, user)  # also bumps the activity clock
    session.commit()
    session.refresh(report)
    return to_out(session, report, user)


def release_lock(session: Session, report_id: uuid.UUID, user: User) -> None:
    report = get_report(session, report_id, for_update=True)
    if report_lock.is_active(report) and report.lock_user_id != user.id:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "The lock is held by another operator"
        )
    report.lock_user_id = None
    report.lock_acquired_at = None
    report.lock_last_activity_at = None
    session.commit()


def force_release(
    session: Session, report_id: uuid.UUID, admin: User, request: Request
) -> None:
    """D4: an admin frees a lock held by someone else; always audited."""
    report = get_report(session, report_id, for_update=True)
    previous = session.get(User, report.lock_user_id) if report_lock.is_active(report) else None
    report.lock_user_id = None
    report.lock_acquired_at = None
    report.lock_last_activity_at = None
    audit.record(
        session, action=AuditAction.lock_override, user_id=admin.id,
        entity_type="report", entity_id=report.id,
        detail={"previous_holder": previous.username if previous else None}, request=request,
    )
    session.commit()


# --- Free-form sections (§15.6) --------------------------------------------

def _locked_draft(session: Session, report_id: uuid.UUID, user: User) -> Report:
    report = get_report(session, report_id, for_update=True)
    report_lock.require_editable(report, user)
    return report


def _get_section(report: Report, section_id: uuid.UUID) -> ReportSection:
    for s in report.sections:
        if s.id == section_id:
            return s
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Section not found")


def add_section(
    session: Session, report_id: uuid.UUID, body: SectionCreate, user: User, request: Request
) -> ReportOut:
    report = _locked_draft(session, report_id, user)
    position = max((s.position for s in report.sections), default=0) + 1
    report.sections.append(
        ReportSection(position=position, title=body.title.strip(),
                      content_markdown=body.content_markdown)
    )
    audit.record(
        session, action=AuditAction.update, user_id=user.id,
        entity_type="report", entity_id=report.id,
        detail={"section_added": body.title.strip()}, request=request,
    )
    session.commit()
    session.refresh(report)
    return to_out(session, report, user)


def update_section(
    session: Session, report_id: uuid.UUID, section_id: uuid.UUID, body: SectionUpdate,
    user: User, request: Request,
) -> ReportOut:
    report = _locked_draft(session, report_id, user)
    section = _get_section(report, section_id)
    changes = body.model_dump(exclude_unset=True)
    if "title" in changes:
        if not (changes["title"] or "").strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "title cannot be empty")
        section.title = changes["title"].strip()
    if "content_markdown" in changes:
        section.content_markdown = changes["content_markdown"]
    audit.record(
        session, action=AuditAction.update, user_id=user.id,
        entity_type="report", entity_id=report.id,
        detail={"section_updated": section.title}, request=request,
    )
    session.commit()
    session.refresh(report)
    return to_out(session, report, user)


def delete_section(
    session: Session, report_id: uuid.UUID, section_id: uuid.UUID, user: User, request: Request
) -> ReportOut:
    report = _locked_draft(session, report_id, user)
    section = _get_section(report, section_id)
    title = section.title
    report.sections.remove(section)
    session.flush()
    # Close the gap, ascending so no two rows ever share a position.
    for index, s in enumerate(sorted(report.sections, key=lambda x: x.position), start=1):
        if s.position != index:
            s.position = index
            session.flush()
    audit.record(
        session, action=AuditAction.update, user_id=user.id,
        entity_type="report", entity_id=report.id,
        detail={"section_removed": title}, request=request,
    )
    session.commit()
    session.refresh(report)
    return to_out(session, report, user)


def reorder_sections(
    session: Session, report_id: uuid.UUID, ids: list[uuid.UUID], user: User, request: Request
) -> ReportOut:
    report = _locked_draft(session, report_id, user)
    existing = {s.id: s for s in report.sections}
    if sorted(map(str, ids)) != sorted(map(str, existing)):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "ids must list every section of the report exactly once",
        )
    # (report_id, position) is unique: park rows on negative positions first.
    for i, sid in enumerate(ids, start=1):
        existing[sid].position = -i
    session.flush()
    for i, sid in enumerate(ids, start=1):
        existing[sid].position = i
    audit.record(
        session, action=AuditAction.update, user_id=user.id,
        entity_type="report", entity_id=report.id,
        detail={"sections_reordered": True}, request=request,
    )
    session.commit()
    session.refresh(report)
    return to_out(session, report, user)


# --- Vulnerabilities inside a report ----------------------------------------

def create_vuln(
    session: Session, report_id: uuid.UUID, body: VulnCreate, user: User, request: Request
) -> Vulnerability:
    report = _locked_draft(session, report_id, user)
    data = body.model_dump(exclude={"operator_ids"})
    vuln = Vulnerability(
        status=VulnStatus.draft, report_id=report.id, created_by=user.id, **data
    )
    vuln.operators = _resolve_operators(session, body.operator_ids)
    session.add(vuln)
    session.flush()
    audit.record(
        session, action=AuditAction.create, user_id=user.id,
        entity_type="vulnerability", entity_id=vuln.id,
        detail={"report_id": str(report.id)}, request=request,
    )
    session.commit()
    session.refresh(vuln)
    return vuln
