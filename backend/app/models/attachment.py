"""Attachments — vuln files and report evidence bundle (SPEC §15.10).

Exactly one owner FK is non-null, enforced by a CHECK constraint.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import UUIDPK


class Attachment(UUIDPK, Base):
    __tablename__ = "attachments"
    __table_args__ = (
        CheckConstraint(
            "(vulnerability_id IS NULL) != (report_id IS NULL)",
            name="ck_attachment_exactly_one_owner",
        ),
    )

    vulnerability_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vulnerabilities.id", ondelete="CASCADE"),
        nullable=True,
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=True,
    )
    s3_key: Mapped[str] = mapped_column(Text, nullable=False)  # MinIO object key
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    # Operator-assigned; for images, used as markdown alt-text ![display_name](url).
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # true -> embedded inline; false -> sent as a file attachment on dispatch.
    is_image: Mapped[bool] = mapped_column(Boolean, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
