"""Report templates: reusable text for a report's sections.

A template holds the executive summary, the introduction and the free-form sections.
Creating a report from one *copies* that text into the report, so later changes to the
template never touch existing reports. Templates belong to the user who saved them;
an admin can make one available to everyone (`is_global`).
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import UUIDPK, Timestamps

if TYPE_CHECKING:
    from app.models.user import User


class ReportTemplate(UUIDPK, Timestamps, Base):
    __tablename__ = "report_templates"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    is_global: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    executive_summary_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    introduction_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    # [{"title": str, "content_markdown": str | None}, ...] in report order.
    sections: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    # Bumped on every edit; a stale client version is rejected with 409 (as for vulns, D5).
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    owner: Mapped["User"] = relationship(lazy="joined")
