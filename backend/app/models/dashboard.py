"""Dashboards and their TV links (D18, docs/specs/DASHBOARDS.md)."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import UUIDPK, Timestamps


class Dashboard(UUIDPK, Timestamps, Base):
    __tablename__ = "dashboards"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # [{"name": "periodo", "value": "90d"}]: `$periodo` in a query becomes `90d`.
    variables: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    # [{"title": "Remediação", "charts": [{"query": "count where …", "width": 1}]}], in display order.
    # The portal pages through the screens; a TV loops over them. width: 1, 2 or 3 columns.
    screens: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    # How often the numbers are recomputed on screen, and how long a TV shows each screen.
    refresh_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("60"))
    rotate_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("30"))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class DashboardLink(UUIDPK, Base):
    """A read-only link to show a dashboard on a TV, without signing in.

    Only a hash of the token is kept (the URL is shown once). It computes with the access of
    whoever made it and accepts only the groupings status, severity and source."""

    __tablename__ = "dashboard_links"

    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)
