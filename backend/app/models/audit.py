"""Audit log — append-only, never updated or deleted (SPEC §15.11).

Exactly one actor (human user OR api key) is non-null, enforced by CHECK.
Read events ARE captured deliberately (D8): confidential findings make
who-read-what-when a security control. Volume is managed operationally.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import AuditAction


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NULL) != (api_key_id IS NULL)",
            name="ck_audit_exactly_one_actor",
        ),
    )

    # bigserial — integer sequence preferred over uuid for an append-only,
    # high-volume table.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True
    )
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action"), nullable=False
    )
    entity_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
