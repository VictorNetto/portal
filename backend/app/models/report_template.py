"""Report templates: reusable text for a report's sections.

A template holds the executive summary, the introduction and the free-form sections.
Creating a report from one *copies* that text into the report, so later changes to the
template never touch existing reports.

Sharing is a reviewed process (D11):
    private --owner requests--> pending --admin approves--> shared
       ^                          |  (admin rejects / owner withdraws -> private)
       |                          v
    shared --admin unshares--> unshared --admin re-shares--> shared
A shared template belongs to everyone: its owner can no longer change or delete it.
An unshared one is available to nobody (its owner included) until an admin shares it again.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import UUIDPK, Timestamps

if TYPE_CHECKING:
    from app.models.user import User


class ShareStatus(str, enum.Enum):
    private = "private"
    pending = "pending"      # the owner asked to share it; waiting for an admin
    shared = "shared"        # approved: available to every user
    unshared = "unshared"    # an admin withdrew it: available to nobody


class ReportTemplate(UUIDPK, Timestamps, Base):
    __tablename__ = "report_templates"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    share_status: Mapped[ShareStatus] = mapped_column(
        Enum(ShareStatus, name="template_share_status"),
        nullable=False, server_default=ShareStatus.private.value,
    )
    share_requested_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # The last admin decision (approve / reject / unshare / re-share), and when.
    share_decided_at: Mapped[datetime | None] = mapped_column(nullable=True)
    share_decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    executive_summary_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    introduction_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    # [{"title": str, "content_markdown": str | None}, ...] in report order.
    sections: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    # Bumped on every edit; a stale client version is rejected with 409 (as for vulns, D5).
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    owner: Mapped["User"] = relationship(foreign_keys=[owner_id], lazy="joined")
    decided_by: Mapped["User | None"] = relationship(foreign_keys=[share_decided_by], lazy="joined")
