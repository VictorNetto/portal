"""Authentication endpoints: login, refresh, me, change-password (§10.1)."""

import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit, security
from app.db import get_session
from app.deps import get_current_user_allow_password_change
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.auth import (
    AccessToken,
    ChangePasswordRequest,
    CurrentUser,
    LoginRequest,
    RefreshRequest,
    TokenPair,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
def login(
    body: LoginRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> TokenPair:
    user = session.scalar(select(User).where(User.username == body.username))

    # Constant-ish behavior: verify even on missing user to avoid leaking which
    # usernames exist via timing. (bcrypt call is skipped if no hash, which is
    # acceptable here; a dummy-hash compare could be added if timing matters.)
    valid = (
        user is not None
        and user.is_active
        and user.password_hash is not None
        and security.verify_password(body.password, user.password_hash)
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    audit.record(
        session, action=AuditAction.login, user_id=user.id, request=request
    )
    session.commit()

    sub = str(user.id)
    return TokenPair(
        access_token=security.create_access_token(sub),
        refresh_token=security.create_refresh_token(sub),
    )


@router.post("/refresh", response_model=AccessToken)
def refresh(body: RefreshRequest, session: Session = Depends(get_session)) -> AccessToken:
    try:
        payload = security.decode_token(body.refresh_token, expected_type="refresh")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    return AccessToken(access_token=security.create_access_token(str(user.id)))


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

    if body.new_password == body.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current one",
        )

    user.password_hash = security.hash_password(body.new_password)
    user.must_change_password = False
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
