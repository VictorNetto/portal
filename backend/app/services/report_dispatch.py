"""Report send and export (SPEC §9, D2).

Sending runs in two phases so a delivery failure can never masquerade as a
completed send:

  Check:  the package is built once first; content that cannot be rendered is refused
          (422) and the report stays an ordinary draft, so it can be corrected.
  Phase 1 (one DB transaction): report frozen (`sending`), OP-xxxx and VULN-xxxx
          ids assigned, lock cleared. Committed before anything is sent.
  Phase 2 (re-locked, outside phase 1): render PDF + Excel, gather non-image
          attachments, call the dispatcher. On success the report and its vulns
          become `sent`. If delivery fails they stay drafts, the report stays frozen
          with the error recorded, and the operator retries the same endpoint. If
          rendering fails, retrying cannot help: the report is unfrozen for correction.
"""

import io
import re
import uuid
import zipfile
from datetime import datetime

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit, dispatcher, render
from app.models.attachment import Attachment
from app.models.enums import AuditAction, ReportStatus, VulnStatus
from app.models.report import Report
from app.models.user import User
from app.models.vulnerability import Vulnerability
from app.schemas.report import ReportOut
from app.services import report as report_svc
from app.services import report_lock
from app.services.vulnerability import _next_vuln_internal_id
from app.storage import get_storage

DISPATCH_TARGET = "blue-team"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _blank(value: str | None) -> bool:
    return not (value or "").strip()


# --- artifact building ---------------------------------------------------------------------

def _owned_attachments(session: Session, report: Report, vulns: list[Vulnerability]) -> list[Attachment]:
    """Attachments of the report (evidence bundle) and of its vulnerabilities."""
    vuln_ids = [v.id for v in vulns]
    stmt = select(Attachment).where(
        (Attachment.report_id == report.id)
        | (Attachment.vulnerability_id.in_(vuln_ids) if vuln_ids else False)
    ).order_by(Attachment.created_at)
    return list(session.scalars(stmt))


def _read(att: Attachment) -> bytes:
    return b"".join(get_storage().open(att.s3_key))


def _image_loader(attachments: list[Attachment]):
    """Only images owned by this report or its vulns may be embedded in its PDF,
    so crafted markdown can't pull in another record's files."""
    images = {str(a.id): a for a in attachments if a.is_image}

    def load(att_id: str):
        att = images.get(att_id)
        if att is None:
            return None
        try:
            return _read(att), att.mime_type
        except Exception:
            return None

    return load


def _file_stem(report: Report) -> str:
    """A draft has no internal ID yet: its files are named after the report."""
    return report.internal_id or _safe_name(report.name)


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip() or "arquivo"


def build_package(session: Session, report: Report, vulns: list[Vulnerability]):
    """(pdf, xlsx, [(filename, bytes)]) for a report and its vulnerabilities."""
    attachments = _owned_attachments(session, report, vulns)
    pdf = render.report_pdf(report, vulns, _image_loader(attachments))
    xlsx = render.vulnerabilities_xlsx(report, vulns)

    vuln_by_id = {v.id: v for v in vulns}
    files: list[tuple[str, bytes]] = []
    used: set[str] = set()
    for att in attachments:
        if att.is_image:
            continue  # images travel inside the PDF
        owner = vuln_by_id.get(att.vulnerability_id)
        prefix = (owner.internal_id or "vuln") if owner else "evidencias"
        name = f"{_safe_name(prefix)}_{_safe_name(att.original_filename)}"
        n = 1
        while name in used:  # keep names unique inside the package
            n += 1
            name = f"{_safe_name(prefix)}_{n}_{_safe_name(att.original_filename)}"
        used.add(name)
        files.append((name, _read(att)))
    return pdf, xlsx, files


def _body(report: Report, vulns: list[Vulnerability]) -> str:
    lines = [
        f"Relatório {report.internal_id}: {report.name}",
        f"Cliente: {report.client_name or '—'}",
        f"Vulnerabilidades: {len(vulns)}",
        "",
    ]
    for v in vulns:
        score = f"{float(v.cvss_score):.1f}" if v.cvss_score is not None else "—"
        lines.append(f"- {v.internal_id}  CVSS {score}  {v.identifier or ''}")
    lines += ["", "Anexos: relatório em PDF, planilha de vulnerabilidades e arquivos de evidência."]
    return "\n".join(lines)


def _unrenderable(exc: Exception) -> HTTPException:
    return HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        f"The report could not be generated, so nothing was sent. Review its content. ({str(exc)[:200]})",
    )


# --- dispatch --------------------------------------------------------------------------------

def send(
    session: Session, report_id: uuid.UUID, user: User, request: Request
) -> ReportOut:
    report = report_svc.get_report(session, report_id, user, for_update=True, write=True)

    if report.status == ReportStatus.sent:
        raise HTTPException(status.HTTP_409_CONFLICT, "The report is already sent")

    if not report.sending:
        # --- preconditions: the caller holds the lock; every vuln has an identifier (D3)
        report_lock.require_editable(report, user)
        vulns = report_svc._vulns_of(session, report)
        missing = [v for v in vulns if _blank(v.identifier)]
        if missing:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"{len(missing)} vulnerability(ies) have no identifier — fill it in before "
                "sending (D3)",
            )
        try:
            build_package(session, report, vulns)
        except Exception as exc:
            raise _unrenderable(exc) from exc
        # --- Phase 1: one atomic transaction
        for v in vulns:  # already CVSS-descending, so VULN numbers follow severity
            # A report unfrozen after a failed render keeps the numbers it already has.
            v.internal_id = v.internal_id or _next_vuln_internal_id(session)
            v.version += 1
        report.internal_id = report.internal_id or report_svc._next_report_internal_id(session)
        report.sending = True
        report.send_error = None
        report.lock_user_id = None
        report.lock_acquired_at = None
        report.lock_last_activity_at = None
        audit.record(
            session, action=AuditAction.send, user_id=user.id,
            entity_type="report", entity_id=report.id,
            detail={"phase": 1, "vulns": len(vulns)}, request=request,
        )
        session.commit()

    # --- Phase 2: render + deliver. Re-lock the row so two retries can't both send.
    report = report_svc.get_report(session, report_id, user, for_update=True, write=True)
    if report.status == ReportStatus.sent:  # a concurrent retry finished first
        raise HTTPException(status.HTTP_409_CONFLICT, "The report is already sent")
    vulns = report_svc._vulns_of(session, report)

    try:
        pdf, xlsx, files = build_package(session, report, vulns)
    except Exception as exc:
        report.sending = False
        report.send_error = None
        audit.record(
            session, action=AuditAction.send, user_id=user.id,
            entity_type="report", entity_id=report.id,
            detail={"phase": 2, "ok": False, "error": str(exc)[:500]}, request=request,
        )
        session.commit()
        raise _unrenderable(exc) from exc

    try:
        payload = dispatcher.DispatchPayload(
            subject=f"[Portal Red Team] {report.internal_id} — {report.name}",
            body=_body(report, vulns),
            attachments=[
                (f"{report.internal_id}.pdf", pdf),
                (f"{report.internal_id}_vulnerabilidades.xlsx", xlsx),
                *files,
            ],
        )
        result = dispatcher.dispatch(DISPATCH_TARGET, payload)
        if not result.ok:
            raise RuntimeError(result.detail or "dispatcher reported a failure")
    except Exception as exc:  # any failure keeps the report frozen, ready for a retry
        report.send_error = str(exc)[:500]
        audit.record(
            session, action=AuditAction.send, user_id=user.id,
            entity_type="report", entity_id=report.id,
            detail={"phase": 2, "ok": False, "error": report.send_error}, request=request,
        )
        session.commit()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Delivery failed; the report was not sent. Try again. ({report.send_error})",
        ) from exc

    now = report_lock.utcnow()
    for v in vulns:
        v.status = VulnStatus.sent
        v.sent_at = now
        v.version += 1
        audit.record(
            session, action=AuditAction.status_change, user_id=user.id,
            entity_type="vulnerability", entity_id=v.id,
            detail={"from": "draft", "to": "sent", "report_id": str(report.id)},
            request=request,
        )
    report.status = ReportStatus.sent
    report.sent_at = now
    report.sending = False
    report.send_error = None
    audit.record(
        session, action=AuditAction.send, user_id=user.id,
        entity_type="report", entity_id=report.id,
        detail={"phase": 2, "ok": True, "transport": result.transport,
                "attachments": len(payload.attachments)}, request=request,
    )
    session.commit()
    session.refresh(report)
    return report_svc.to_out(session, report, user)


# --- export (no state change) -------------------------------------------------------------------

def export_report(
    session: Session, report_id: uuid.UUID, fmt: str, user: User, request: Request
) -> tuple[bytes, str, str]:
    """(bytes, media_type, filename). Internal notes are never included."""
    if fmt not in ("pdf", "xlsx", "docx"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "format must be pdf, xlsx or docx")
    return export_report_obj(session, report_svc.get_report(session, report_id, user), fmt, user, request)


def export_report_obj(
    session: Session, report: Report, fmt: str, actor, request: Request
) -> tuple[bytes, str, str]:
    """Export a report the caller may read; `actor` is a user or an API key."""
    if fmt not in ("pdf", "xlsx", "docx"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "format must be pdf, xlsx or docx")
    vulns = report_svc._vulns_of(session, report)
    if fmt == "docx":
        docx_bytes = render.report_docx(report, vulns, _image_loader(_owned_attachments(session, report, vulns)))
        audit.record(
            session, action=AuditAction.export, **audit.by(actor),
            entity_type="report", entity_id=report.id, detail={"format": fmt}, request=request,
        )
        session.commit()
        return (docx_bytes, DOCX_MIME,
                f"{_file_stem(report)}_{datetime.now().strftime('%Y%m%d')}.docx")
    pdf, xlsx, _files = build_package(session, report, vulns)
    audit.record(
        session, action=AuditAction.export, **audit.by(actor),
        entity_type="report", entity_id=report.id, detail={"format": fmt}, request=request,
    )
    session.commit()
    stamp = datetime.now().strftime("%Y%m%d")
    if fmt == "pdf":
        return pdf, "application/pdf", f"{_file_stem(report)}_{stamp}.pdf"
    return (
        xlsx,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        f"{_file_stem(report)}_vulnerabilidades_{stamp}.xlsx",
    )


MAX_BATCH = 200


def _unique(name: str, used: set[str]) -> str:
    base, dot, ext = name.rpartition(".")
    candidate, n = name, 1
    while candidate in used:
        n += 1
        candidate = f"{base}_{n}.{ext}" if dot else f"{name}_{n}"
    used.add(candidate)
    return candidate


def _batch_ids(ids: list[uuid.UUID]) -> list[uuid.UUID]:
    unique = list(dict.fromkeys(ids))
    if not unique:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Select at least one item")
    if len(unique) > MAX_BATCH:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"At most {MAX_BATCH} items per export"
        )
    return unique


def export_vulnerabilities_batch(
    session: Session, ids: list[uuid.UUID], fmt: str, user: User, request: Request
) -> tuple[bytes, str, str]:
    """Selected vulnerabilities as a ZIP of PDFs (one each) or one Excel sheet."""
    from app.services import vulnerability as vuln_svc

    if fmt not in ("pdf", "xlsx"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "format must be pdf or xlsx")
    vulns = [vuln_svc.get_visible(session, i, user) for i in _batch_ids(ids)]  # 404 if any is missing
    stamp = datetime.now().strftime("%Y%m%d_%H%M")

    if fmt == "xlsx":
        data = render.vulnerabilities_xlsx(None, vulns)
        media, filename = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            f"vulnerabilidades_{stamp}.xlsx",
        )
    else:
        out, used = io.BytesIO(), set()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for v in vulns:
                owned = list(session.scalars(select(Attachment).where(Attachment.vulnerability_id == v.id)))
                label = _safe_name(v.internal_id or (v.identifier or "vulnerabilidade")[:40])
                z.writestr(_unique(f"{label}.pdf", used),
                           render.vulnerability_pdf(v, _image_loader(owned)))
        data, media, filename = out.getvalue(), "application/zip", f"vulnerabilidades_{stamp}.zip"

    audit.record(
        session, action=AuditAction.export, user_id=user.id, entity_type="vulnerability",
        detail={"format": fmt, "count": len(vulns), "batch": True}, request=request,
    )
    session.commit()
    return data, media, filename


def export_reports_batch(
    session: Session, ids: list[uuid.UUID], user: User, request: Request
) -> tuple[bytes, str, str]:
    """Selected reports as a ZIP of PDFs (one each)."""
    reports = [report_svc.get_report(session, i, user) for i in _batch_ids(ids)]
    out, used = io.BytesIO(), set()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for r in reports:
            vulns = report_svc._vulns_of(session, r)
            pdf, _xlsx, _files = build_package(session, r, vulns)
            z.writestr(_unique(f"{_file_stem(r)}.pdf", used), pdf)
    audit.record(
        session, action=AuditAction.export, user_id=user.id, entity_type="report",
        detail={"format": "pdf", "count": len(reports), "batch": True}, request=request,
    )
    session.commit()
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return out.getvalue(), "application/zip", f"relatorios_{stamp}.zip"


def export_vulnerability_pdf(
    session: Session, vuln: Vulnerability, user, request: Request, fmt: str = "pdf"
) -> tuple[bytes, str, str]:
    """`user` is whoever exports: a user or an API key (it is only audited)."""
    owned = list(session.scalars(select(Attachment).where(Attachment.vulnerability_id == vuln.id)))
    if fmt == "docx":
        data, media, ext = render.vulnerability_docx(vuln, _image_loader(owned)), DOCX_MIME, "docx"
    else:
        data, media, ext = render.vulnerability_pdf(vuln, _image_loader(owned)), "application/pdf", "pdf"
    audit.record(
        session, action=AuditAction.export, **audit.by(user),
        entity_type="vulnerability", entity_id=vuln.id, detail={"format": ext}, request=request,
    )
    session.commit()
    return data, media, f"{vuln.internal_id or 'vulnerabilidade'}.{ext}"
