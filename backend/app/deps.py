"""FastAPI dependencies for authentication and authorization.

`get_current_user` is the gate every protected route depends on: it validates
the bearer access token, loads the user, and rejects inactive accounts.
`require_roles(...)` builds a dependency that additionally enforces role.
"""

import uuid
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.enums import UserRole
from app.models.user import User
from app.security import decode_token

# auto_error=False so we can raise our own 401 with a clear message.
_bearer = HTTPBearer(auto_error=False)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user_allow_password_change(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    if creds is None:
        raise _CREDENTIALS_EXC
    try:
        payload = decode_token(creds.credentials, expected_type="access")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _CREDENTIALS_EXC

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXC
    return user


# Returned as the 403 `detail` so clients can tell it apart from a role denial.
PASSWORD_CHANGE_REQUIRED = "password_change_required"


def get_current_user(
    user: User = Depends(get_current_user_allow_password_change),
) -> User:
    """The gate every protected route depends on.

    Beyond authentication it enforces the first-login rule: an account flagged
    `must_change_password` can reach nothing except the endpoints that use
    `get_current_user_allow_password_change` (/auth/me, /auth/change-password).
    The flag is read from the DB on each request, so it takes effect at once
    (e.g. right after an admin resets someone's password).
    """
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=PASSWORD_CHANGE_REQUIRED
        )
    return user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    """Dependency factory: require the current user to hold one of `roles`."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return checker
