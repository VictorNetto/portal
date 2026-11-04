"""What the defense team sees of a vulnerability (D17).

Its own shape on purpose: only what the red team sends, never internal notes, operators,
sharing, the creator or anything about the report beyond its name.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import VulnStatus


class DefenseReportRef(BaseModel):
    id: uuid.UUID
    internal_id: str | None
    name: str

    model_config = {"from_attributes": True}


class DefenseUserRef(BaseModel):
    username: str

    model_config = {"from_attributes": True}


class DefenseVulnItem(BaseModel):
    id: uuid.UUID
    internal_id: str | None
    status: VulnStatus
    identifier: str | None
    cvss_score: Decimal | None
    rvs_id: str | None
    report: DefenseReportRef | None = None
    sent_at: datetime | None
    accepted_at: datetime | None
    risk_accepted_at: datetime | None
    fixing_at: datetime | None
    retesting_at: datetime | None
    fixed_at: datetime | None

    model_config = {"from_attributes": True}


class DefenseVuln(DefenseVulnItem):
    cwe: str | None
    cvss_vector: str | None
    description: str | None
    finding_detail: str | None
    mitigation: str | None
    references: list[str] = Field(default_factory=list)
    accepter: DefenseUserRef | None = None
    risk_accepter: DefenseUserRef | None = None
    risk_reason: str | None = None


class DefenseAttachment(BaseModel):
    id: uuid.UUID
    original_filename: str
    display_name: str | None
    mime_type: str
    size_bytes: int
    is_image: bool

    model_config = {"from_attributes": True}


class DefenseRiskAccept(BaseModel):
    reason: str = Field(min_length=5, max_length=2000)


class DefenseRvs(BaseModel):
    rvs_id: str = Field(min_length=1, max_length=200)
