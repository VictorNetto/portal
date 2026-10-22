"""Reports, report sections, and report-operator links — SPEC §15.5–15.7."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import ReportStatus
from app.models.mixins import UUIDPK, Timestamps

if TYPE_CHECKING:
    from app.models.user import User

# §15.7 — many-to-many between reports and users (assigned operators).
report_operators = Table(
    "report_operators",
    Base.metadata,
    Column(
        "report_id",
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        primary_key=True,
    ),
)


# D10 — users a report is explicitly shared with (read access for restricted readers).
report_viewers = Table(
    "report_viewers",
    Base.metadata,
    Column(
        "report_id",
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
)


class Report(UUIDPK, Timestamps, Base):
    __tablename__ = "reports"

    # OP-0007; assigned from report_seq on first save.
    internal_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    client_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"),
        nullable=False,
        server_default=ReportStatus.draft.value,
    )
    # D2 — last dispatch-phase-2 failure message; set while stuck in
    # `dispatching`, cleared on success.
    dispatch_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Report content (§7) stored as columns.
    executive_summary_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    introduction_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    demand_origin: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_model: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Editable even after dispatch; excluded from exports.
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    dispatched_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Write lock (§3). Idle-release at lock_last_activity_at + 10 min (lazy check).
    lock_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    lock_acquired_at: Mapped[datetime | None] = mapped_column(nullable=True)
    lock_last_activity_at: Mapped[datetime | None] = mapped_column(nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # The template the report was created from (its text was copied; kept for traceability).
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_templates.id", ondelete="SET NULL"), nullable=True
    )

    sections: Mapped[list["ReportSection"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
    operators: Mapped[list["User"]] = relationship(secondary=report_operators)
    viewers: Mapped[list["User"]] = relationship(secondary=report_viewers)


class ReportSection(UUIDPK, Timestamps, Base):
    """Free-form extra sections only (§15.6). The five typed sections live as
    columns on `reports`. Rendered after Report Data, before the vulns."""

    __tablename__ = "report_sections"
    __table_args__ = (
        UniqueConstraint("report_id", "position", name="uq_report_section_position"),
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-based
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)

    report: Mapped["Report"] = relationship(back_populates="sections")
