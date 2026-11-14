"""User management schemas (SPEC §10.2)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import UserRole


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=8)
    role: UserRole


class UserUpdate(BaseModel):
    """Admin edit: role and/or active flag. Username is immutable once set."""

    role: UserRole | None = None
    is_active: bool | None = None


class PasswordReset(BaseModel):
    """Admin-set new password; forces a change on next login."""

    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    role: UserRole
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AccessItem(BaseModel):
    """One record a user can reach, and why (created / operator / shared / report)."""

    id: uuid.UUID
    internal_id: str | None
    title: str | None
    status: str
    relations: list[str]


class UserAccess(BaseModel):
    """What a user can read. Roles that read everything report scope "all" and no list."""

    scope: str  # "all" | "restricted" | "sent" (defense, D17) | "aggregates" (dashboard, D18)
    vulnerabilities: list[AccessItem] = Field(default_factory=list)
    reports: list[AccessItem] = Field(default_factory=list)

