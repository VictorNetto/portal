"""Attachment rules: what may be uploaded, to which vuln, and how it is stored.

The client's Content-Type is never trusted. The type is derived from the file
extension (allowlist) and then cross-checked against the file's leading bytes,
so a renamed executable or script can't pass as an image/PDF. SVG is excluded
on purpose (it can carry script).
"""

import uuid
from pathlib import PurePosixPath, PureWindowsPath

from fastapi import HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.models.attachment import Attachment
from app.models.enums import AuditAction, VulnStatus
from app.models.user import User
from app.models.vulnerability import Vulnerability
from app.services import vulnerability as vuln_svc
from app.storage import get_storage

MAX_BYTES = 50 * 1024 * 1024  # 50 MB per file (prototype / FRONTEND_SPEC §8)

# extension -> (mime, is_image)
_TYPES: dict[str, tuple[str, bool]] = {
    "png": ("image/png", True),
    "jpg": ("image/jpeg", True),
    "jpeg": ("image/jpeg", True),
    "gif": ("image/gif", True),
    "webp": ("image/webp", True),
    "pdf": ("application/pdf", False),
    "zip": ("application/zip", False),
    "txt": ("text/plain", False),
    "csv": ("text/csv", False),
}

# Attachments follow the vuln's content-field lock (SPEC §4): only editable
# while the vuln is still a draft / saved locally.
_ATTACHABLE = {VulnStatus.draft, VulnStatus.saved_local}


def _looks_like_text(head: bytes) -> bool:
    if b"\x00" in head:
        return False
    # The sample may end mid-way through a multibyte character; allow for that.
    for trim in range(4):
        try:
            head[: len(head) - trim].decode("utf-8")
            return True
        except UnicodeDecodeError:
            continue
    return False


def _magic_ok(ext: str, head: bytes) -> bool:
    if ext == "png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in ("jpg", "jpeg"):
        return head.startswith(b"\xff\xd8\xff")
    if ext == "gif":
        return head.startswith((b"GIF87a", b"GIF89a"))
    if ext == "webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    if ext == "pdf":
        return head.startswith(b"%PDF-")
    if ext == "zip":
        return head.startswith((b"PK\x03\x04", b"PK\x05\x06"))
    return _looks_like_text(head)  # txt / csv


def _safe_filename(raw: str | None) -> str:
    # Drop any directory part (either separator style) and control characters.
    name = PurePosixPath(PureWindowsPath(raw or "").name).name
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    return name[:255] or "file"


def get_editable_vuln(
    session: Session, vuln_id: uuid.UUID, user: User | None = None
) -> Vulnerability:
    vuln = vuln_svc.get_visible(session, vuln_id)
    if vuln_svc.is_in_report(vuln):
        # Inside a draft report: same rule as the vuln's own fields (§3) — the
        # caller must hold the report lock.
        if user is not None:
            vuln_svc._require_report_lock(session, vuln, user)
        return vuln
    if vuln.status not in _ATTACHABLE:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Attachments are locked in status '{vuln.status.value}'",
        )
    return vuln


def list_for_vuln(session: Session, vuln_id: uuid.UUID) -> list[Attachment]:
    vuln_svc.get_visible(session, vuln_id)  # 404 if missing/deleted
    return list(
        session.scalars(
            select(Attachment)
            .where(Attachment.vulnerability_id == vuln_id)
            .order_by(Attachment.created_at)
        )
    )


def get(session: Session, attachment_id: uuid.UUID) -> Attachment:
    att = session.get(Attachment, attachment_id)
    if att is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attachment not found")
    # Files of a deleted vulnerability must stop being readable.
    if att.vulnerability_id is not None:
        owner = session.get(Vulnerability, att.vulnerability_id)
        if owner is None or owner.deleted_at is not None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Attachment not found")
    return att


def add(
    session: Session,
    vuln_id: uuid.UUID,
    upload: UploadFile,
    display_name: str | None,
    user: User,
    request: Request,
) -> Attachment:
    vuln = get_editable_vuln(session, vuln_id, user)

    filename = _safe_filename(upload.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Unsupported file type. Allowed: " + ", ".join(sorted(_TYPES)),
        )
    mime, is_image = _TYPES[ext]

    fileobj = upload.file
    fileobj.seek(0, 2)
    size = fileobj.tell()
    fileobj.seek(0)
    if size == 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "The file is empty")
    if size > MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds the 50 MB limit"
        )
    if not _magic_ok(ext, fileobj.read(8192)):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "File content does not match its extension",
        )
    fileobj.seek(0)

    key = f"vulnerabilities/{vuln.id}/{uuid.uuid4()}"
    storage = get_storage()
    storage.put(key, fileobj, size, mime)

    name = (display_name or "").strip() or None
    att = Attachment(
        vulnerability_id=vuln.id,
        s3_key=key,
        original_filename=filename,
        display_name=name[:200] if name else None,
        mime_type=mime,
        size_bytes=size,
        is_image=is_image,
        uploaded_by=user.id,
    )
    session.add(att)
    try:
        session.flush()
        audit.record(
            session, action=AuditAction.create, user_id=user.id,
            entity_type="attachment", entity_id=att.id,
            detail={"vulnerability_id": str(vuln.id), "filename": filename, "size": size},
            request=request,
        )
        session.commit()
    except Exception:
        session.rollback()
        storage.delete(key)  # don't leave an orphan object behind
        raise
    session.refresh(att)
    return att


def remove(session: Session, attachment_id: uuid.UUID, user: User, request: Request) -> None:
    att = get(session, attachment_id)
    if att.vulnerability_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attachment not found")
    get_editable_vuln(session, att.vulnerability_id, user)

    key, filename, vuln_id = att.s3_key, att.original_filename, att.vulnerability_id
    session.delete(att)
    audit.record(
        session, action=AuditAction.delete, user_id=user.id,
        entity_type="attachment", entity_id=attachment_id,
        detail={"vulnerability_id": str(vuln_id), "filename": filename}, request=request,
    )
    session.commit()
    # Delete the object only after the DB commit succeeded; a failure here just
    # leaves an unreferenced object, never a dangling DB row.
    get_storage().delete(key)
