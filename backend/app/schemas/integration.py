"""What the integration API (/v1, API keys) returns (D13).

Kept apart from the UI schemas on purpose: integrations get a stable shape that
does not follow UI changes, and never carry internal notes, viewers or locks.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class ExtReportRef(BaseModel):
    id: uuid.UUID
    internal_id: str | None
    name: str
    status: str


class ExtVulnSummary(BaseModel):
    id: uuid.UUID
    internal_id: str | None
    status: str
    identifier: str | None
    cwe: str | None
    cvss_score: float | None          # a JSON number, not a string
    source: str | None
    rvs_id: str | None
    report: ExtReportRef | None
    created_at: datetime
    updated_at: datetime


class ExtVuln(ExtVulnSummary):
    description: str | None
    finding_detail: str | None
    mitigation: str | None
    references: list[str]
    cvss_vector: str | None
    operators: list[str]           # usernames
    metadata: dict
    ready_at: datetime | None
    sent_at: datetime | None
    fixing_at: datetime | None
    retesting_at: datetime | None
    fixed_at: datetime | None


class ExtAttachment(BaseModel):
    id: uuid.UUID
    filename: str
    display_name: str | None
    mime_type: str
    size_bytes: int
    created_at: datetime


class ExtSection(BaseModel):
    position: int
    title: str
    content_markdown: str | None


class ExtReportSummary(BaseModel):
    id: uuid.UUID
    internal_id: str | None
    name: str
    client_name: str | None
    status: str
    start_date: date | None
    end_date: date | None
    sent_at: datetime | None
    vulnerability_count: int
    fixed_count: int               # how many of them are fixed: the report's progress
    created_at: datetime
    updated_at: datetime


class ExtReport(ExtReportSummary):
    test_type: str | None
    test_model: str | None
    environment: str | None
    demand_origin: str | None
    scope: str | None
    executive_summary_md: str | None
    introduction_md: str | None
    sections: list[ExtSection]
    operators: list[str]
    vulnerabilities: list[ExtVulnSummary]
    attachments: list[ExtAttachment]   # the report's evidence


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None = Field(description="Pass as ?cursor= for the next page; null at the end")


class RvsBody(BaseModel):
    rvs_id: str = Field(min_length=1, max_length=200)
