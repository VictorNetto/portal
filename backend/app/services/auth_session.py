"""Login sessions and login throttling (D16).

Every login opens a row here and its tokens carry the row's id, so a session can be ended
on the server: signing out, changing a password, or replaying an old refresh token.

Failed logins are audited, and that audit trail is also what the limit counts: it needs no
extra store and works across workers.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app import security
from app.models.audit import AuditLog
from app.models.enums import AuditAction
from app.models.user import AuthSession, User
from app.services.report_lock import utcnow

FAILED_WINDOW = timedelta(minutes=15)
MAX_FAILED_PER_ACCOUNT = 5
MAX_FAILED_PER_IP = 30
# Two tabs may refresh with the same token at once; only a later reuse is a replay.
REUSE_GRACE = timedelta(seconds=30)


def _failed(session: Session, since: datetime, *condition) -> int:
    return session.scalar(select(func.count()).select_from(AuditLog).where(
        AuditLog.action == AuditAction.login_failed, AuditLog.created_at > since, *condition)) or 0


def blocked(session: Session, username: str, ip: str | None, user: User | None) -> bool:
    since = utcnow() - FAILED_WINDOW
    account_since = since
    if user is not None:  # a success clears the account's failures
        last = session.scalar(select(func.max(AuditLog.created_at)).where(
            AuditLog.action == AuditAction.login, AuditLog.user_id == user.id))
        account_since = max(since, last) if last else since
    if _failed(session, account_since, AuditLog.detail["username"].astext == username[:150]) >= MAX_FAILED_PER_ACCOUNT:
        return True
    return bool(ip) and _failed(session, since, AuditLog.ip_address == ip) >= MAX_FAILED_PER_IP


def open(session: Session, user_id: uuid.UUID, jti: str) -> AuthSession:
    now = utcnow()
    session.execute(delete(AuthSession).where(AuthSession.user_id == user_id, AuthSession.expires_at < now))
    row = AuthSession(user_id=user_id, refresh_jti=jti,
                      expires_at=now + timedelta(minutes=security.settings.session_max_minutes))
    session.add(row)
    session.flush()
    return row


def rotate(session: Session, sid: uuid.UUID, user_id: uuid.UUID, jti: str) -> AuthSession | None:
    """The session with a new refresh token, or None when `jti` may not be used. An old
    token used after the grace period means a copy exists, so the session ends."""
    row = session.scalar(select(AuthSession).where(AuthSession.id == sid).with_for_update())
    if row is None or row.user_id != user_id or row.revoked_at is not None:
        return None
    now = utcnow()
    racing = jti == row.previous_jti and row.rotated_at and now - row.rotated_at <= REUSE_GRACE
    if jti != row.refresh_jti and not racing:
        row.revoked_at = now
        return None
    row.previous_jti, row.refresh_jti, row.rotated_at = row.refresh_jti, security.new_token_id(), now
    return row


def revoke(session: Session, sid: uuid.UUID) -> None:
    session.execute(update(AuthSession).where(AuthSession.id == sid).values(revoked_at=utcnow()))


def revoke_all(session: Session, user_id: uuid.UUID, keep: uuid.UUID | None = None) -> None:
    conditions = [AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)]
    if keep is not None:
        conditions.append(AuthSession.id != keep)
    session.execute(update(AuthSession).where(*conditions).values(revoked_at=utcnow()))
