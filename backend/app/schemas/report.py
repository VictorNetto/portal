"""Report request/response schemas (SPEC §6, §7, §15.5–15.7)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ReportStatus
from app.schemas.vulnerability import OperatorRef, VulnListItem


class LockInfo(BaseModel):
    """Who holds the report's write lock (§3). Absent when nobody does."""

    holder_id: uuid.UUID
    holder_username: str
    acquired_at: datetime
    expires_at: datetime  # when it frees itself if the holder stays idle
    mine: bool


class SectionOut(BaseModel):
    id: uuid.UUID
    position: int
    title: str
    content_markdown: str | None

    model_config = {"from_attributes": True}


class SectionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content_markdown: str | None = Field(default=None, max_length=200_000)


class SectionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content_markdown: str | None = Field(default=None, max_length=200_000)


class SectionReorder(BaseModel):
    ids: list[uuid.UUID]


def _check_dates(start: date | None, end: date | None) -> None:
    if start and end and end < start:
        raise ValueError("end_date must not be before start_date")


class ReportCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    client_name: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    operator_ids: list[uuid.UUID] = Field(default_factory=list)
    viewer_ids: list[uuid.UUID] = Field(default_factory=list)
    # Start from this template's text (copied). None: the standard starting text.
    template_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _dates(self) -> "ReportCreate":
        _check_dates(self.start_date, self.end_date)
        return self


class ReportUpdate(BaseModel):
    """Partial update; only the fields that are sent change.
    `operator_ids`, when provided, replaces the full operator set."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    client_name: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    executive_summary_md: str | None = Field(default=None, max_length=200_000)
    introduction_md: str | None = Field(default=None, max_length=200_000)
    test_type: str | None = Field(default=None, max_length=200)
    demand_origin: str | None = Field(default=None, max_length=200)
    environment: str | None = Field(default=None, max_length=200)
    scope: str | None = Field(default=None, max_length=5000)
    test_model: str | None = Field(default=None, max_length=200)
    internal_notes: str | None = Field(default=None, max_length=200_000)
    operator_ids: list[uuid.UUID] | None = None
    viewer_ids: list[uuid.UUID] | None = None


class ReportListItem(BaseModel):
    id: uuid.UUID
    internal_id: str | None
    name: str
    client_name: str | None
    status: ReportStatus
    operators: list[OperatorRef] = Field(default_factory=list)
    viewers: list[OperatorRef] = Field(default_factory=list)
    created_by: uuid.UUID
    vuln_count: int = 0
    max_cvss: Decimal | None = None
    start_date: date | None
    end_date: date | None
    lock: LockInfo | None = None
    dispatched_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReportOut(ReportListItem):
    dispatch_error: str | None
    executive_summary_md: str | None
    introduction_md: str | None
    test_type: str | None
    demand_origin: str | None
    environment: str | None
    scope: str | None
    test_model: str | None
    internal_notes: str | None
    sections: list[SectionOut] = Field(default_factory=list)
    vulnerabilities: list[VulnListItem] = Field(default_factory=list)
