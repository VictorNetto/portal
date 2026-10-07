"""Report write lock (SPEC §3, D4).

Only the report carries a lock; holding it grants write access to the report and
to every vulnerability linked to it. The lock frees itself after 10 minutes of
inactivity — checked lazily, no background job. Dispatched reports skip locking.
"""

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from app.models.enums import ReportStatus
from app.models.report import Report
from app.models.user import User

LOCK_TTL = timedelta(minutes=10)


def utcnow() -> datetime:
    """Naive UTC, matching how timestamps are stored."""
    return datetime.now(UTC).replace(tzinfo=None)


def is_active(report: Report, now: datetime | None = None) -> bool:
    now = now or utcnow()
    return bool(
        report.lock_user_id
        and report.lock_last_activity_at
        and now - report.lock_last_activity_at < LOCK_TTL
    )


def held_by(report: Report, user: User, now: datetime | None = None) -> bool:
    return is_active(report, now) and report.lock_user_id == user.id


def touch(report: Report) -> None:
    """Any write bumps the activity clock, extending the idle window."""
    report.lock_last_activity_at = utcnow()


def require_editable(report: Report, user: User) -> None:
    """Gate for every write to a draft report or its vulns: the report must be a
    draft and the caller must hold the lock. Bumps activity on success."""
    if report.status == ReportStatus.dispatching:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "The report is being dispatched and is locked"
        )
    if report.status == ReportStatus.dispatched:
        raise HTTPException(status.HTTP_409_CONFLICT, "A dispatched report is immutable")
    if not held_by(report, user):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "You do not hold the report lock. Acquire it to edit this report.",
        )
    touch(report)
