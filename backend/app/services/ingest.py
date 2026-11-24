"""Inbound vulnerability creation by machine callers (SPEC §11)."""

from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import audit, scopes
from app.models.enums import AuditAction, UserRole, VulnStatus
from app.models.user import ApiKey, User
from app.models.vulnerability import VulnBatch, Vulnerability
from app.schemas.ingest import IngestVuln, IngestVulnUpdate
from app.services import vulnerability as vuln_svc
from app.services.vulnerability import _next_vuln_internal_id, _require_unused_rvs

# Same fields the UI requires before a vuln can be sent (FRONTEND_SPEC §8.8).
_REQUIRED_FOR_READY = ("identifier", "description", "finding_detail")  # mitigation may stay blank


def _blank(value: str | None) -> bool:
    return not (value or "").strip()


def _resolve_operators(session: Session, usernames: list[str]) -> list[User]:
    if not usernames:
        return []
    wanted = list(dict.fromkeys(u.strip() for u in usernames if u.strip()))
    users = list(session.scalars(select(User).where(User.username.in_(wanted))))
    by_name = {u.username: u for u in users}
    unknown = [n for n in wanted if n not in by_name]
    # Operators must be real, active accounts that are allowed to work on vulns.
    unusable = [
        n for n, u in by_name.items()
        if not u.is_active or u.role not in (UserRole.admin, UserRole.write_all, UserRole.write_restricted)
    ]
    if unknown or unusable:
        problems = []
        if unknown:
            problems.append("unknown operator(s): " + ", ".join(unknown))
        if unusable:
            problems.append("operator(s) not active writers: " + ", ".join(unusable))
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "; ".join(problems))
    return [by_name[n] for n in wanted]


def create(
    session: Session, payload: IngestVuln, key: ApiKey, request: Request
) -> Vulnerability:
    # A history needs vulns:import: said before anything about the content.
    used = payload.import_fields_used()
    if used and scopes.VULNS_IMPORT not in (key.scopes or []):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"This API key lacks the scope 'vulns:import', needed for: {', '.join(used)}",
        )
    if not any(not _blank(getattr(payload, f)) for f in ("identifier", "description", "finding_detail")):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Provide at least one of: identifier, description, finding_detail",
        )
    if payload.status != "draft":
        missing = [f for f in _REQUIRED_FOR_READY if _blank(getattr(payload, f))]
        if missing:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Required for status '{payload.status}': " + ", ".join(missing),
            )
    if used:
        return _import(session, payload, key, request)

    batch_id = _resolve_batch(session, payload.batch_id)
    operators = _resolve_operators(session, payload.operators)
    vuln = Vulnerability(
        status=VulnStatus.draft,
        identifier=payload.identifier,
        cwe=payload.cwe,
        description=payload.description,
        finding_detail=payload.finding_detail,
        mitigation=payload.mitigation,
        references=payload.references,
        cvss_score=payload.cvss_score,
        cvss_vector=payload.cvss_vector,
        source=payload.source,
        internal_notes=payload.internal_notes,
        extra_metadata=payload.combined_metadata(),
        batch_id=batch_id,
        # The record belongs to whoever issued the key; the key itself is the
        # actor in the audit log.
        created_by=key.created_by,
    )
    vuln.operators = operators
    session.add(vuln)
    session.flush()

    audit.record(
        session, action=AuditAction.create, api_key_id=key.id,
        entity_type="vulnerability", entity_id=vuln.id,
        detail={"via": "api", "source": payload.source, "status": payload.status, "batch": batch_id},
        request=request,
    )
    if payload.status == "ready":
        vuln.status = VulnStatus.ready
        vuln.ready_at = datetime.now(UTC)
        vuln.internal_id = _next_vuln_internal_id(session)
        vuln.version += 1
        audit.record(
            session, action=AuditAction.status_change, api_key_id=key.id,
            entity_type="vulnerability", entity_id=vuln.id,
            detail={"from": "draft", "to": "ready"}, request=request,
        )
    session.commit()
    session.refresh(vuln)
    return vuln


# --- Imports (vulns:import) -------------------------------------------------------
# A past vulnerability arrives as it ended up: its status and the date of each step that
# led there, as the portal itself would have recorded them. Nothing is sent and no
# history is made up: one audit entry says it was imported.

_IMPORT_DATES = (
    "created_at", "ready_at", "sent_at", "accepted_at", "fixing_at", "retesting_at", "fixed_at",
    "risk_accepted_at",
)
# Per status: the dates it must have, and those it may have.
_REQUIRED_DATES: dict[str, tuple[str, ...]] = {
    "draft": ("created_at",),
    "ready": ("created_at", "ready_at"),
    "sent": ("created_at", "ready_at", "sent_at"),
    "risk_accepted": ("created_at", "ready_at", "sent_at", "risk_accepted_at"),
    "fixing": ("created_at", "ready_at", "sent_at", "fixing_at"),
    "retesting": ("created_at", "ready_at", "sent_at", "fixing_at", "retesting_at"),
    "fixed": ("created_at", "ready_at", "sent_at", "fixing_at", "fixed_at"),
}
_OPTIONAL_DATES: dict[str, tuple[str, ...]] = {
    "sent": ("accepted_at",),
    "risk_accepted": ("accepted_at",),
    "fixing": ("accepted_at",),       # recording the RVS ID accepts it: defaults to fixing_at
    "retesting": ("accepted_at",),
    "fixed": ("accepted_at", "retesting_at"),   # the defense team may close it without a retest
}
# (earlier, later): when both are present, the first may not come after the second.
_ORDER = (
    ("created_at", "ready_at"), ("ready_at", "sent_at"), ("sent_at", "accepted_at"),
    ("sent_at", "fixing_at"), ("accepted_at", "fixing_at"), ("sent_at", "risk_accepted_at"),
    ("accepted_at", "risk_accepted_at"), ("fixing_at", "retesting_at"),
    ("fixing_at", "fixed_at"), ("retesting_at", "fixed_at"),
)
_WITH_RVS = ("fixing", "retesting", "fixed")


def _unprocessable(problems: list[str]) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "; ".join(problems))


def _user_id(session: Session, field: str, username: str | None, problems: list[str]):
    if username is None or not username.strip():
        return None
    user_id = session.scalar(select(User.id).where(User.username == username.strip()))
    if user_id is None:
        problems.append(f"{field}: unknown user '{username.strip()}'")
    return user_id


def _history(session: Session, p: IngestVuln) -> dict:
    """The lifecycle columns of an imported vuln, checked against its status; 422 otherwise."""
    st = p.status
    dates = {f: getattr(p, f) for f in _IMPORT_DATES if getattr(p, f) is not None}
    required, optional = _REQUIRED_DATES[st], _OPTIONAL_DATES.get(st, ())
    problems = []
    missing = [f for f in required if f not in dates]
    if missing:
        problems.append(f"status '{st}' needs: " + ", ".join(missing))
    extra = [f for f in dates if f not in required and f not in optional]
    if extra:
        problems.append(f"not part of status '{st}': " + ", ".join(extra))
    for earlier, later in _ORDER:
        if earlier in dates and later in dates and dates[earlier] > dates[later]:
            problems.append(f"{earlier} is after {later}")

    rvs = (p.rvs_id or "").strip() or None
    if st in _WITH_RVS and rvs is None:
        problems.append(f"status '{st}' needs: rvs_id")
    if st not in _WITH_RVS and rvs is not None:
        problems.append(f"not part of status '{st}': rvs_id")
    if st in _WITH_RVS and "accepted_at" not in dates and "fixing_at" in dates:
        dates["accepted_at"] = dates["fixing_at"]
    if st == "risk_accepted":
        if _blank(p.risk_reason):
            problems.append("status 'risk_accepted' needs: risk_reason")
    else:
        problems += [f"not part of status '{st}': {f}"
                     for f in ("risk_reason", "risk_accepted_by") if not _blank(getattr(p, f))]
    if not _blank(p.accepted_by) and "accepted_at" not in dates:
        problems.append("accepted_by needs accepted_at")
    if st == "draft" and p.internal_id:
        problems.append("a draft has no internal_id")

    latest = max(dates.values()) if dates else None
    updated = p.updated_at or latest
    if p.updated_at and latest and p.updated_at < latest:
        problems.append("updated_at is before the last of its dates")

    accepted_by = _user_id(session, "accepted_by", p.accepted_by, problems)
    risk_by = _user_id(session, "risk_accepted_by", p.risk_accepted_by, problems)
    if problems:
        raise _unprocessable(problems)
    return {
        **dates, "updated_at": updated, "rvs_id": rvs, "accepted_by": accepted_by,
        "risk_accepted_by": risk_by,
        "risk_reason": p.risk_reason.strip() if st == "risk_accepted" else None,
    }


def _number(session: Session, wanted: str | None) -> str:
    """Its original VULN number (the counter moves past it, so new ones never collide), or the
    next one."""
    if wanted is None:
        return _next_vuln_internal_id(session)
    if session.scalar(select(Vulnerability.id).where(Vulnerability.internal_id == wanted)):
        raise HTTPException(status.HTTP_409_CONFLICT, f"{wanted} already exists")
    session.execute(
        text("SELECT setval('vuln_seq', GREATEST(:n, (SELECT last_value FROM vuln_seq)))"),
        {"n": int(wanted.split("-")[1])},
    )
    return wanted


def _import(session: Session, p: IngestVuln, key: ApiKey, request: Request) -> Vulnerability:
    history = _history(session, p)
    if history["rvs_id"]:
        _require_unused_rvs(session, history["rvs_id"])
    batch_id = _resolve_batch(session, p.batch_id)
    operators = _resolve_operators(session, p.operators)
    internal_id = None if p.status == "draft" else _number(session, p.internal_id)
    vuln = Vulnerability(
        status=VulnStatus(p.status), internal_id=internal_id,
        identifier=p.identifier, cwe=p.cwe, description=p.description,
        finding_detail=p.finding_detail, mitigation=p.mitigation, references=p.references,
        cvss_score=p.cvss_score, cvss_vector=p.cvss_vector, source=p.source,
        internal_notes=p.internal_notes, extra_metadata=p.combined_metadata(),
        batch_id=batch_id, created_by=key.created_by, imported_at=datetime.now(UTC),
        **history,
    )
    vuln.operators = operators
    session.add(vuln)
    try:
        session.flush()
    except IntegrityError:  # the same number or RVS ID imported at the same moment
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "internal_id or rvs_id already exists") from None
    audit.record(
        session, action=AuditAction.create, api_key_id=key.id,
        entity_type="vulnerability", entity_id=vuln.id,
        detail={"via": "api", "import": True, "source": p.source, "status": p.status,
                "internal_id": internal_id, "batch": batch_id},
        request=request,
    )
    session.commit()
    session.refresh(vuln)
    return vuln


# --- Batches -------------------------------------------------------------------

def create_batch(session: Session, key: ApiKey, request: Request) -> VulnBatch:
    """A new batch id for the vulns of one tool run."""
    n = session.execute(text("SELECT nextval('vuln_batch_seq')")).scalar_one()
    batch = VulnBatch(internal_id=f"BATCH-{n:04d}", api_key_id=key.id)
    session.add(batch)
    session.flush()
    audit.record(
        session, action=AuditAction.create, api_key_id=key.id,
        entity_type="vuln_batch", entity_id=batch.id,
        detail={"batch": batch.internal_id}, request=request,
    )
    session.commit()
    session.refresh(batch)
    return batch


def _resolve_batch(session: Session, ref: str | None) -> str | None:
    """The stored id of an existing batch ('batch-0001' is fine); 422 if there is none."""
    if ref is None or not ref.strip():
        return None
    wanted = ref.strip().upper()
    if session.scalar(select(VulnBatch.internal_id).where(VulnBatch.internal_id == wanted)) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Unknown batch_id '{ref.strip()}': create one with POST /v1/batches",
        )
    return wanted


_REQUIRES_ONE_OF = ("identifier", "description", "finding_detail")


def update(
    session: Session, vuln: Vulnerability, payload: IngestVulnUpdate, key: ApiKey, request: Request
) -> Vulnerability:
    """Edit a draft or ready vulnerability through the API: the fields sent, nothing else.

    The lifecycle (completing, sending, ...) stays in the portal. A vuln inside a draft report
    is edited there too, under the report's lock (SPEC §3)."""
    changes = payload.model_dump(exclude_unset=True)
    expected = changes.pop("if_updated_at", None)
    if vuln.status not in (VulnStatus.draft, VulnStatus.ready):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Only a draft or ready vulnerability can be edited (current: {vuln.status.value})",
        )
    if vuln_svc.is_in_report(vuln):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This vulnerability is inside a draft report: edit it in the portal, under the report's lock",
        )
    if expected is not None and expected != vuln.updated_at:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Changed since {expected.isoformat()} (now {vuln.updated_at.isoformat()}): read it again",
        )

    if "batch_id" in changes:  # null takes it out of its batch
        changes["batch_id"] = _resolve_batch(session, changes["batch_id"])
    new_ops = _resolve_operators(session, changes.pop("operators") or []) if "operators" in changes else None

    after = {f: changes.get(f, getattr(vuln, f)) for f in _REQUIRED_FOR_READY}
    if vuln.status == VulnStatus.ready:
        missing = [f for f in _REQUIRED_FOR_READY if _blank(after[f])]
        if missing:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Required for status 'ready': " + ", ".join(missing),
            )
    elif all(_blank(after[f]) for f in _REQUIRES_ONE_OF):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Provide at least one of: identifier, description, finding_detail",
        )

    changed = [f for f, v in changes.items() if getattr(vuln, f) != v]
    detail: dict = {"via": "api"}
    if "batch_id" in changed:
        detail["batch"] = {"from": vuln.batch_id, "to": changes["batch_id"]}
    for f in changed:
        setattr(vuln, f, changes[f])
    if new_ops is not None and {u.id for u in new_ops} != {u.id for u in vuln.operators}:
        vuln.operators = new_ops
        changed.append("operators")
    if not changed:
        return vuln  # nothing to change: no new version, no audit entry

    vuln.version += 1  # D5: an open editor in the portal sees the change as a conflict
    audit.record(
        session, action=AuditAction.update, api_key_id=key.id,
        entity_type="vulnerability", entity_id=vuln.id,
        detail={**detail, "fields": changed}, request=request,
    )
    session.commit()
    session.refresh(vuln)
    return vuln
