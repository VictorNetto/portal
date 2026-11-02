"""Authentication endpoints: login, refresh, logout, me, change-password (§10.1, D16)."""

import uuid
from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit, security
from app.config import settings
from app.db import get_session
from app.deps import get_current_user_allow_password_change, require_password_fits
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    CurrentUser,
    LoginRequest,
    RefreshRequest,
    TokenPair,
)
from app.services import auth_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
def login(
    body: LoginRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> TokenPair:
    user = session.scalar(select(User).where(User.username == body.username))
    ip = audit.client_ip(request)
    if auth_session.blocked(session, body.username, ip, user):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Too many failed attempts. Try again later.",
            headers={"Retry-After": str(int(auth_session.FAILED_WINDOW.total_seconds()))},
        )

    matches = security.verify_password_or_nothing(body.password, user.password_hash if user else None)
    if not matches or not user.is_active:
        audit.record(
            session, action=AuditAction.login_failed, user_id=user.id if user else None,
            detail={"username": body.username[:150]}, request=request,
        )
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    audit.record(
        session, action=AuditAction.login, user_id=user.id, request=request
    )
    jti = security.new_token_id()
    row = auth_session.open(session, user.id, jti)
    tokens = _tokens(user.id, row, jti)
    row.expires_at = tokens.session_expires_at.astimezone(UTC).replace(tzinfo=None)
    session.commit()
    return tokens


def _tokens(user_id: uuid.UUID, row, jti: str, started: datetime | None = None) -> TokenPair:
    access, refresh, end = security.create_session_tokens(str(user_id), str(row.id), jti, started)
    return TokenPair(
        access_token=access, refresh_token=refresh, session_expires_at=end,
        idle_timeout_seconds=settings.session_idle_minutes * 60,
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, session: Session = Depends(get_session)) -> TokenPair:
    """Renew an active session: a fresh refresh token (idle window restarts)
    but the same session start, so the 1 h limit never moves (D12)."""
    try:
        payload = security.decode_token(body.refresh_token, expected_type="refresh")
        user_id = uuid.UUID(payload["sub"])
        sid = uuid.UUID(payload["sid"])
        jti = payload["jti"]
        started = datetime.fromtimestamp(int(payload["sst"]), UTC)
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from None

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    if security.session_end(started) <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    row = auth_session.rotate(session, sid, user.id, jti)
    session.commit()  # a replayed token has just ended its session
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    return _tokens(user.id, row, row.refresh_jti, started)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    user: User = Depends(get_current_user_allow_password_change),
    session: Session = Depends(get_session),
) -> None:
    auth_session.revoke(session, request.state.session_id)
    audit.record(session, action=AuditAction.logout, user_id=user.id, request=request)
    session.commit()


@router.get("/me", response_model=CurrentUser)
def me(user: User = Depends(get_current_user_allow_password_change)) -> User:
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user: User = Depends(get_current_user_allow_password_change),
    session: Session = Depends(get_session),
) -> None:
    if user.password_hash is None or not security.verify_password(
        body.current_password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters",
        )

    require_password_fits(body.new_password)
    if body.new_password == body.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current one",
        )

    user.password_hash = security.hash_password(body.new_password)
    user.must_change_password = False
    auth_session.revoke_all(session, user.id, keep=request.state.session_id)
    audit.record(
        session,
        action=AuditAction.update,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        detail={"field": "password"},
        request=request,
    )
    session.commit()
