"""Record-level access rules (D10).

Role gates on routes decide *who may try*; this module decides *on which records*.

- `admin`, `write_all`, `read_all`, `auditor` see everything; `admin` and `write_all`
  change everything.
- `write_restricted` creates its own records and changes the ones it created or
  operates. It may delete only what it created.
- `read_restricted` reads only records it created, operates or was shared with
  (`viewers`). A report's vulnerabilities follow the report's access.
- `defense` never reaches these routes (deps.get_current_user refuses it); its own
  rules are in services/defense.py (D17).

A record a user may not read answers 404, never 403, so its existence is not revealed.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.report import Report, report_operators, report_viewers
from app.models.user import User
from app.models.vulnerability import Vulnerability, vulnerability_operators, vulnerability_viewers

_READ_ALL = {UserRole.admin, UserRole.write_all, UserRole.read_all, UserRole.auditor}
_WRITE_ALL = {UserRole.admin, UserRole.write_all}
_CREATORS = _WRITE_ALL | {UserRole.write_restricted}

FORBIDDEN = "Insufficient permissions"


def reads_all(user: User) -> bool:
    return user.role in _READ_ALL


def writes_all(user: User) -> bool:
    return user.role in _WRITE_ALL


def can_create(user: User) -> bool:
    return user.role in _CREATORS


def _involved(user: User, rec: Vulnerability | Report) -> bool:
    return rec.created_by == user.id or any(o.id == user.id for o in rec.operators)


def _shared_with(user: User, rec: Vulnerability | Report) -> bool:
    return any(v.id == user.id for v in rec.viewers)


# --- Reports ------------------------------------------------------------------

def can_read_report(user: User, report: Report) -> bool:
    return reads_all(user) or _involved(user, report) or _shared_with(user, report)


def can_write_report(user: User, report: Report) -> bool:
    return writes_all(user) or (user.role == UserRole.write_restricted and _involved(user, report))


def can_delete_report(user: User, report: Report) -> bool:
    return writes_all(user) or (
        user.role == UserRole.write_restricted and report.created_by == user.id
    )


# --- Vulnerabilities ----------------------------------------------------------

def _report_of(session: Session, vuln: Vulnerability) -> Report | None:
    return session.get(Report, vuln.report_id) if vuln.report_id else None


def can_read_vuln(session: Session, user: User, vuln: Vulnerability) -> bool:
    if reads_all(user) or _involved(user, vuln) or _shared_with(user, vuln):
        return True
    report = _report_of(session, vuln)
    return report is not None and can_read_report(user, report)


def can_write_vuln(session: Session, user: User, vuln: Vulnerability) -> bool:
    if writes_all(user):
        return True
    if user.role != UserRole.write_restricted:
        return False
    if _involved(user, vuln):
        return True
    report = _report_of(session, vuln)
    return report is not None and can_write_report(user, report)


def can_delete_vuln(session: Session, user: User, vuln: Vulnerability) -> bool:
    if writes_all(user):
        return True
    if user.role != UserRole.write_restricted:
        return False
    if vuln.created_by == user.id:
        return True
    report = _report_of(session, vuln)
    return report is not None and can_write_report(user, report)


# --- Enforcement ----------------------------------------------------------------

def _forbidden() -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, FORBIDDEN)


def require_read_vuln(session: Session, user: User, vuln: Vulnerability) -> None:
    if not can_read_vuln(session, user, vuln):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vulnerability not found")


def require_write_vuln(session: Session, user: User, vuln: Vulnerability) -> None:
    if not can_write_vuln(session, user, vuln):
        if not can_read_vuln(session, user, vuln):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vulnerability not found")
        raise _forbidden()


def require_delete_vuln(session: Session, user: User, vuln: Vulnerability) -> None:
    if not can_delete_vuln(session, user, vuln):
        require_read_vuln(session, user, vuln)
        raise _forbidden()


def require_read_report(user: User, report: Report) -> None:
    if not can_read_report(user, report):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")


def require_write_report(user: User, report: Report) -> None:
    if not can_write_report(user, report):
        require_read_report(user, report)
        raise _forbidden()


def require_delete_report(user: User, report: Report) -> None:
    if not can_delete_report(user, report):
        require_read_report(user, report)
        raise _forbidden()


# --- List filters (SQL) -----------------------------------------------------------

def report_visible_clause(user: User):
    """WHERE clause limiting reports to the ones `user` may read; None = no limit."""
    if reads_all(user):
        return None
    uid = user.id
    return or_(
        Report.created_by == uid,
        exists().where(report_operators.c.report_id == Report.id, report_operators.c.user_id == uid),
        exists().where(report_viewers.c.report_id == Report.id, report_viewers.c.user_id == uid),
    )


def vuln_visible_clause(user: User):
    """WHERE clause limiting vulnerabilities to the ones `user` may read; None = no limit."""
    if reads_all(user):
        return None
    uid = user.id
    reports = report_visible_clause(user)
    return or_(
        Vulnerability.created_by == uid,
        exists().where(
            vulnerability_operators.c.vulnerability_id == Vulnerability.id,
            vulnerability_operators.c.user_id == uid,
        ),
        exists().where(
            vulnerability_viewers.c.vulnerability_id == Vulnerability.id,
            vulnerability_viewers.c.user_id == uid,
        ),
        Vulnerability.report_id.in_(select(Report.id).where(reports)),
    )


def resolve_users(
    session: Session, ids: list[uuid.UUID], what: str, keep: list[User] | None = None
) -> list[User]:
    """Users by id for an operator/viewer list; 422 when one is unknown, or inactive and
    not already on the list (`keep`): a deactivated account stays where it was, but
    cannot be newly assigned."""
    if not ids:
        return []
    users = list(session.scalars(select(User).where(User.id.in_(ids))))
    missing = [str(i) for i in ids if i not in {u.id for u in users}]
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown {what} id(s): {', '.join(missing)}"
        )
    defense = [u.username for u in users if u.role == UserRole.defense]
    if defense:  # D17: the defense team receives vulns, it does not work on them
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"A defense account cannot be a {what}: {', '.join(defense)}",
        )
    already = {u.id for u in keep or []}
    inactive = [u.username for u in users if not u.is_active and u.id not in already]
    if inactive:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Inactive {what}(s): {', '.join(inactive)}"
        )
    return users
