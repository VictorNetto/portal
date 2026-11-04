"""Integration API for other systems: /v1, authenticated by API key scopes (D13).

The only place API keys work: they cannot reach the UI endpoints, user
management or the audit log, whatever scopes they carry.

Keys read every record their scope allows (per-user restrictions are for people,
not systems). Records are addressed by UUID or by their number (VULN-0001,
OP-0001). Lists are keyset-paginated in `updated_at` order, which also makes
`updated_since` + `next_cursor` a simple way to sync. Internal notes never leave
through this API, as in the exports.
"""

import base64
import uuid
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from app import audit, scopes
from app.db import get_session
from app.deps import require_scope
from app.models.attachment import Attachment
from app.models.enums import AuditAction, ReportStatus, VulnStatus
from app.models.report import Report
from app.models.user import ApiKey
from app.models.vulnerability import Vulnerability
from app.schemas.ingest import IngestResult, IngestVuln
from app.schemas.integration import (
    ExtAttachment,
    ExtReport,
    ExtReportRef,
    ExtReportSummary,
    ExtSection,
    ExtVuln,
    ExtVulnSummary,
    Page,
    RvsBody,
)
from app.services import ingest as ingest_svc
from app.services import report as report_svc
from app.services import report_dispatch
from app.services import vulnerability as vuln_svc
from app.storage import get_storage

router = APIRouter(prefix="/v1", tags=["integration"])

MAX_PAGE = 200
MAX_BODY_BYTES = 1024 * 1024  # 1 MB per create request


def _limit_body(request: Request) -> None:
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Payload exceeds 1 MB")


# --- helpers -----------------------------------------------------------------

def _naive_utc(dt: datetime | None) -> datetime | None:
    if dt is None or dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)


def _cursor(row) -> str:
    raw = f"{row.updated_at.isoformat()}|{row.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _after(cursor: str | None):
    if not cursor:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        ts, rid = raw.split("|")
        return datetime.fromisoformat(ts), uuid.UUID(rid)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid cursor") from None


def _page(session: Session, model, conditions: list, cursor: str | None, limit: int):
    after = _after(cursor)
    if after:
        conditions = [*conditions, tuple_(model.updated_at, model.id) > after]
    rows = list(session.scalars(
        select(model).where(*conditions).order_by(model.updated_at, model.id).limit(limit + 1)
    ))
    more = len(rows) > limit
    rows = rows[:limit]
    return rows, (_cursor(rows[-1]) if more and rows else None)


def _ref_clause(model, ref: str):
    try:
        return model.id == uuid.UUID(ref)
    except ValueError:
        return func.upper(model.internal_id) == ref.upper()


def _vuln(session: Session, ref: str, *, for_update: bool = False) -> Vulnerability:
    stmt = select(Vulnerability).where(
        _ref_clause(Vulnerability, ref), Vulnerability.deleted_at.is_(None))
    vuln = session.scalar(stmt.with_for_update() if for_update else stmt)
    if vuln is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vulnerability not found")
    return vuln


def _report(session: Session, ref: str) -> Report:
    report = session.scalar(select(Report).where(_ref_clause(Report, ref), Report.deleted_at.is_(None)))
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return report


def _report_ref(r: Report | None) -> ExtReportRef | None:
    return r and ExtReportRef(id=r.id, internal_id=r.internal_id, name=r.name, status=r.status.value)


def _vuln_summary(v: Vulnerability) -> ExtVulnSummary:
    return ExtVulnSummary(
        id=v.id, internal_id=v.internal_id, status=v.status.value, identifier=v.identifier,
        cwe=v.cwe, cvss_score=v.cvss_score, source=v.source, rvs_id=v.rvs_id,
        report=_report_ref(v.report), created_at=v.created_at, updated_at=v.updated_at,
    )


def _vuln_full(v: Vulnerability) -> ExtVuln:
    return ExtVuln(
        **_vuln_summary(v).model_dump(),
        description=v.description, finding_detail=v.finding_detail, mitigation=v.mitigation,
        references=v.references or [], cvss_vector=v.cvss_vector,
        operators=sorted(u.username for u in v.operators), metadata=v.extra_metadata or {},
        ready_at=v.ready_at, sent_at=v.sent_at, accepted_at=v.accepted_at,
        risk_accepted_at=v.risk_accepted_at, risk_reason=v.risk_reason, fixing_at=v.fixing_at,
        retesting_at=v.retesting_at, fixed_at=v.fixed_at,
    )


def _attachment(a: Attachment) -> ExtAttachment:
    return ExtAttachment(id=a.id, filename=a.original_filename, display_name=a.display_name,
                         mime_type=a.mime_type, size_bytes=a.size_bytes, created_at=a.created_at)


def _report_summary(session: Session, r: Report) -> ExtReportSummary:
    vulns = report_svc._vulns_of(session, r)
    return ExtReportSummary(
        id=r.id, internal_id=r.internal_id, name=r.name, client_name=r.client_name,
        status=r.status.value, start_date=r.start_date, end_date=r.end_date,
        sent_at=r.sent_at, vulnerability_count=len(vulns),
        fixed_count=sum(v.status == VulnStatus.fixed for v in vulns),
        closed_count=sum(v.status in (VulnStatus.fixed, VulnStatus.risk_accepted) for v in vulns),
        created_at=r.created_at, updated_at=r.updated_at,
    )


def _file(data: bytes, media_type: str, filename: str) -> Response:
    return Response(content=data, media_type=media_type, headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})


# --- vulnerabilities -----------------------------------------------------------

@router.post("/vulnerabilities", response_model=IngestResult, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(_limit_body)])
def create_vulnerability(
    payload: IngestVuln, request: Request,
    key: ApiKey = Depends(require_scope(scopes.VULNS_WRITE)),
    session: Session = Depends(get_session),
) -> IngestResult:
    """Create a vulnerability, as a draft or already saved (SPEC §11)."""
    vuln = ingest_svc.create(session, payload, key, request)
    return IngestResult(id=vuln.id, internal_id=vuln.internal_id, status=vuln.status.value)


@router.get("/vulnerabilities", response_model=Page[ExtVulnSummary])
def list_vulnerabilities(
    status_: list[VulnStatus] = Query(default=[], alias="status"),
    source: str | None = Query(default=None, description="source contains (case-insensitive)"),
    report: str | None = Query(default=None, description="report UUID or number, or 'none'"),
    cvss_min: float | None = Query(default=None, ge=0, le=10),
    updated_since: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=MAX_PAGE),
    cursor: str | None = None,
    _: ApiKey = Depends(require_scope(scopes.VULNS_READ)),
    session: Session = Depends(get_session),
):
    conditions = [Vulnerability.deleted_at.is_(None)]
    if status_:
        conditions.append(Vulnerability.status.in_(status_))
    if source:
        conditions.append(Vulnerability.source.ilike(f"%{source}%"))
    if report == "none":
        conditions.append(Vulnerability.report_id.is_(None))
    elif report:
        conditions.append(Vulnerability.report_id == _report(session, report).id)
    if cvss_min is not None:
        conditions.append(Vulnerability.cvss_score >= cvss_min)
    if updated_since:
        conditions.append(Vulnerability.updated_at >= _naive_utc(updated_since))
    rows, nxt = _page(session, Vulnerability, conditions, cursor, limit)
    return Page[ExtVulnSummary](items=[_vuln_summary(v) for v in rows], next_cursor=nxt)


@router.get("/vulnerabilities/{ref}", response_model=ExtVuln)
def get_vulnerability(
    ref: str, request: Request,
    key: ApiKey = Depends(require_scope(scopes.VULNS_READ)),
    session: Session = Depends(get_session),
):
    vuln = _vuln(session, ref)
    audit.record(session, action=AuditAction.read, api_key_id=key.id,
                 entity_type="vulnerability", entity_id=vuln.id, request=request)
    session.commit()
    return _vuln_full(vuln)


@router.get("/vulnerabilities/{ref}/attachments", response_model=list[ExtAttachment])
def vulnerability_attachments(
    ref: str,
    _: ApiKey = Depends(require_scope(scopes.VULNS_READ)),
    session: Session = Depends(get_session),
):
    vuln = _vuln(session, ref)
    rows = session.scalars(select(Attachment).where(Attachment.vulnerability_id == vuln.id)
                           .order_by(Attachment.created_at))
    return [_attachment(a) for a in rows]


@router.get("/vulnerabilities/{ref}/export")
def export_vulnerability(
    ref: str, request: Request,
    format: Literal["pdf", "docx"] = "pdf",
    key: ApiKey = Depends(require_scope(scopes.EXPORTS)),
    session: Session = Depends(get_session),
):
    data, media, filename = report_dispatch.export_vulnerability_pdf(
        session, _vuln(session, ref), key, request, format)
    return _file(data, media, filename)


@router.post("/vulnerabilities/{ref}/rvs", response_model=ExtVuln)
def set_rvs(
    ref: str, body: RvsBody, request: Request,
    key: ApiKey = Depends(require_scope(scopes.RVS_WRITE)),
    session: Session = Depends(get_session),
):
    """Record the RVS ID of a sent vulnerability: it moves to fixing."""
    return _vuln_full(vuln_svc.apply_rvs(session, _vuln(session, ref, for_update=True), body.rvs_id, key, request))


@router.get("/rvs-queue", response_model=list[ExtVulnSummary])
def rvs_queue(
    _: ApiKey = Depends(require_scope(scopes.RVS_WRITE, scopes.VULNS_READ)),
    session: Session = Depends(get_session),
):
    """Sent vulnerabilities still waiting for an RVS ID, oldest first."""
    rows = session.scalars(select(Vulnerability).where(
        Vulnerability.deleted_at.is_(None), Vulnerability.status == VulnStatus.sent,
        Vulnerability.rvs_id.is_(None),
    ).order_by(Vulnerability.sent_at))
    return [_vuln_summary(v) for v in rows]


# --- attachments ---------------------------------------------------------------

@router.get("/attachments/{attachment_id}/content")
def attachment_content(
    attachment_id: uuid.UUID, request: Request,
    key: ApiKey = Depends(require_scope(scopes.VULNS_READ, scopes.REPORTS_READ)),
    session: Session = Depends(get_session),
):
    att = session.get(Attachment, attachment_id)
    # Evidence of a vulnerability needs vulns:read; of a report, reports:read.
    needed = scopes.VULNS_READ if att and att.vulnerability_id else scopes.REPORTS_READ
    owner_live = att and (
        (att.vulnerability_id and session.scalar(select(Vulnerability.id).where(
            Vulnerability.id == att.vulnerability_id, Vulnerability.deleted_at.is_(None))))
        or (att.report_id and session.scalar(select(Report.id).where(
            Report.id == att.report_id, Report.deleted_at.is_(None))))
    )
    if not owner_live or needed not in key.scopes:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attachment not found")
    audit.record(session, action=AuditAction.read, api_key_id=key.id, entity_type="attachment",
                 entity_id=att.id, detail={"filename": att.original_filename}, request=request)
    session.commit()
    return StreamingResponse(get_storage().open(att.s3_key), media_type=att.mime_type, headers={
        "X-Content-Type-Options": "nosniff",
        "Content-Length": str(att.size_bytes),
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(att.original_filename)}",
    })


# --- reports -------------------------------------------------------------------

@router.get("/reports", response_model=Page[ExtReportSummary])
def list_reports(
    status_: list[ReportStatus] = Query(default=[], alias="status"),
    client: str | None = Query(default=None, description="client name contains (case-insensitive)"),
    updated_since: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=MAX_PAGE),
    cursor: str | None = None,
    _: ApiKey = Depends(require_scope(scopes.REPORTS_READ)),
    session: Session = Depends(get_session),
):
    conditions = [Report.deleted_at.is_(None)]
    if status_:
        conditions.append(Report.status.in_(status_))
    if client:
        conditions.append(Report.client_name.ilike(f"%{client}%"))
    if updated_since:
        conditions.append(Report.updated_at >= _naive_utc(updated_since))
    rows, nxt = _page(session, Report, conditions, cursor, limit)
    return Page[ExtReportSummary](items=[_report_summary(session, r) for r in rows], next_cursor=nxt)


@router.get("/reports/{ref}", response_model=ExtReport)
def get_report(
    ref: str, request: Request,
    key: ApiKey = Depends(require_scope(scopes.REPORTS_READ)),
    session: Session = Depends(get_session),
):
    r = _report(session, ref)
    audit.record(session, action=AuditAction.read, api_key_id=key.id,
                 entity_type="report", entity_id=r.id, request=request)
    session.commit()
    evidence = session.scalars(select(Attachment).where(Attachment.report_id == r.id)
                               .order_by(Attachment.created_at))
    return ExtReport(
        **_report_summary(session, r).model_dump(),
        test_type=r.test_type, test_model=r.test_model, environment=r.environment,
        demand_origin=r.demand_origin, scope=r.scope,
        executive_summary_md=r.executive_summary_md, introduction_md=r.introduction_md,
        sections=[ExtSection(position=s.position, title=s.title, content_markdown=s.content_markdown)
                  for s in sorted(r.sections, key=lambda s: s.position)],
        operators=sorted(u.username for u in r.operators),
        vulnerabilities=[_vuln_summary(v) for v in report_svc._vulns_of(session, r)],
        attachments=[_attachment(a) for a in evidence],
    )


@router.get("/reports/{ref}/export")
def export_report(
    ref: str, request: Request,
    format: Literal["pdf", "xlsx", "docx"] = "pdf",
    key: ApiKey = Depends(require_scope(scopes.EXPORTS)),
    session: Session = Depends(get_session),
):
    data, media, filename = report_dispatch.export_report_obj(
        session, _report(session, ref), format, key, request)
    return _file(data, media, filename)

