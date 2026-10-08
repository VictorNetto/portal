"""User management endpoints (SPEC §10.2). Admin-managed.

Listing is available to any writer/admin (needed for operator-assignment
pickers); create/update/reset/deactivate are admin-only.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import audit, security
from app.db import get_session
from app.deps import require_roles
from app.models.enums import AuditAction, UserRole
from app.models.user import User
from app.schemas.user import PasswordReset, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

_admin = require_roles(UserRole.admin)
_writer = require_roles(UserRole.admin, UserRole.write_all, UserRole.write_restricted)


@router.get("", response_model=list[UserOut])
def list_users(
    include_inactive: bool = True,
    _: User = Depends(_writer),
    session: Session = Depends(get_session),
) -> list:
    stmt = select(User).order_by(User.username)
    if not include_inactive:
        stmt = stmt.where(User.is_active.is_(True))
    return list(session.scalars(stmt))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    request: Request,
    admin: User = Depends(_admin),
    session: Session = Depends(get_session),
) -> UserOut:
    user = User(
        username=body.username,
        password_hash=security.hash_password(body.password),
        role=body.role,
        must_change_password=True,  # new users change password on first login
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already exists") from None
    audit.record(
        session, action=AuditAction.create, user_id=admin.id,
        entity_type="user", entity_id=user.id,
        detail={"username": user.username, "role": user.role.value}, request=request,
    )
    session.commit()
    session.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: uuid.UUID,
    _: User = Depends(_writer),
    session: Session = Depends(get_session),
) -> UserOut:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    request: Request,
    admin: User = Depends(_admin),
    session: Session = Depends(get_session),
) -> UserOut:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    # Guard against an admin locking themselves out.
    if user.id == admin.id:
        if body.is_active is False:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate yourself")
        if body.role is not None and body.role != UserRole.admin:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot change your own admin role")

    changes = {}
    if body.role is not None and body.role != user.role:
        changes["role"] = {"from": user.role.value, "to": body.role.value}
        user.role = body.role
    if body.is_active is not None and body.is_active != user.is_active:
        changes["is_active"] = {"from": user.is_active, "to": body.is_active}
        user.is_active = body.is_active

    if changes:
        audit.record(
            session, action=AuditAction.permission_change, user_id=admin.id,
            entity_type="user", entity_id=user.id, detail=changes, request=request,
        )
    session.commit()
    session.refresh(user)
    return user


@router.post("/{user_id}/reset-password", response_model=UserOut)
def reset_password(
    user_id: uuid.UUID,
    body: PasswordReset,
    request: Request,
    admin: User = Depends(_admin),
    session: Session = Depends(get_session),
) -> UserOut:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.password_hash = security.hash_password(body.new_password)
    user.must_change_password = True
    audit.record(
        session, action=AuditAction.update, user_id=admin.id,
        entity_type="user", entity_id=user.id, detail={"field": "password_reset"},
        request=request,
    )
    session.commit()
    session.refresh(user)
    return user
