"""What a user can reach, for the admin's user-detail screen (D10).

Reuses the exact SQL filters that restrict the lists, so what the admin sees here is
what the user sees there. Roles that read everything report scope "all" and no list.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import access
from app.models.report import Report
from app.models.user import User
from app.models.vulnerability import Vulnerability
from app.schemas.user import AccessItem, UserAccess

LIMIT = 500


def _relations(user: User, rec: Vulnerability | Report, via_report: bool) -> list[str]:
    out = []
    if rec.created_by == user.id:
        out.append("created")
    if any(o.id == user.id for o in rec.operators):
        out.append("operator")
    if any(v.id == user.id for v in rec.viewers):
        out.append("shared")
    if not out and via_report:
        out.append("report")
    return out


def for_user(session: Session, user: User) -> UserAccess:
    if access.reads_all(user):
        return UserAccess(scope="all")

    reports = session.scalars(
        select(Report)
        .where(Report.deleted_at.is_(None), access.report_visible_clause(user))
        .order_by(Report.updated_at.desc())
        .limit(LIMIT)
    )
    vulns = session.scalars(
        select(Vulnerability)
        .where(Vulnerability.deleted_at.is_(None), access.vuln_visible_clause(user))
        .order_by(Vulnerability.updated_at.desc())
        .limit(LIMIT)
    )
    return UserAccess(
        scope="restricted",
        vulnerabilities=[
            AccessItem(
                id=v.id, internal_id=v.internal_id, title=v.identifier,
                status=v.status.value, relations=_relations(user, v, v.report_id is not None),
            )
            for v in vulns
        ],
        reports=[
            AccessItem(
                id=r.id, internal_id=r.internal_id, title=r.name,
                status=r.status.value, relations=_relations(user, r, False),
            )
            for r in reports
        ],
    )
