"""Users and API keys — SPEC §15.3, §15.4."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Enum, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import UserRole
from app.models.mixins import Timestamps, UUIDPK


class User(UUIDPK, Timestamps, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    # bcrypt (passwords are low-entropy, D7). NULL reserved for future SSO-only accounts.
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )


class ApiKey(UUIDPK, Base):
    __tablename__ = "api_keys"

    label: Mapped[str] = mapped_column(Text, nullable=False)
    # First 8 chars of the plaintext key, shown in UI for identification.
    key_prefix: Mapped[str] = mapped_column(Text, nullable=False)
    # Full key hashed with SHA-256 (D7); key is 32+ bytes CSPRNG so a fast hash
    # is safe. Plaintext shown exactly once at creation.
    key_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", create_type=False), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
