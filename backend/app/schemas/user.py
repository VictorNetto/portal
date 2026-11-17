"""User management schemas (SPEC §10.2)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import UserRole


def _clean_name(v: str | None) -> str | None:
    """Trimmed, inner whitespace collapsed; blank means "not set"."""
    if v is None:
        return None
    v = " ".join(v.split())
    return v or None


class NameFields(BaseModel):
    """The person's names (not the login). Blank clears a name."""

    full_name: str | None = Field(default=None, max_length=150)
    display_name: str | None = Field(default=None, max_length=60)

    _clean = field_validator("full_name", "display_name")(_clean_name)


class UserCreate(NameFields):
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=8)
    role: UserRole


class UserUpdate(NameFields):
    """Admin edit: role, active flag and/or names. Username is immutable once set.
    A name is changed only when it is sent (see model_fields_set)."""

    role: UserRole | None = None
    is_active: bool | None = None


class ProfileUpdate(NameFields):
    """The user's own names (Perfil page). Both are always sent; blank clears."""


class PasswordReset(BaseModel):
    """Admin-set new password; forces a change on next login."""

    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str | None
    display_name: str | None
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

