"""Inbound (machine) vulnerability payload — SPEC §11.

Required-ness depends on the requested initial status (see services/ingest.py):
a `draft` only needs *something* meaningful, while `ready` needs the same
fields the UI demands before "Concluir". Unknown top-level fields are accepted and
kept as extra metadata, so scanners can send their own data without us having
to model it.

A key that also holds `vulns:import` may bring a past vulnerability with its history: any
status, the dates of each step, its VULN number and RVS ID (IMPORT_FIELDS). The same body,
without that scope, may not use them (services/ingest.py).
"""

import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.vulnerability import http_references, normalise_cwe

MAX_METADATA_BYTES = 64 * 1024

# Lifecycle dates a past vulnerability may bring (vulns:import), in their order.
DATE_FIELDS = (
    "created_at", "ready_at", "sent_at", "accepted_at", "fixing_at", "retesting_at", "fixed_at",
    "risk_accepted_at", "updated_at",
)
IMPORT_FIELDS = (
    "internal_id", "rvs_id", *DATE_FIELDS, "accepted_by", "risk_accepted_by", "risk_reason",
)


class IngestVuln(BaseModel):
    model_config = ConfigDict(extra="allow")

    identifier: str | None = Field(default=None, max_length=500)
    cwe: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=100_000)
    finding_detail: str | None = Field(default=None, max_length=100_000)
    mitigation: str | None = Field(default=None, max_length=100_000)
    references: list[str] = Field(default_factory=list, max_length=50)
    cvss_score: Decimal | None = Field(default=None, ge=0, le=10)
    cvss_vector: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default=None, max_length=200)
    internal_notes: str | None = Field(default=None, max_length=100_000)
    # From POST /v1/batches (BATCH-0001): groups the vulns of one tool run.
    batch_id: str | None = Field(default=None, max_length=32)

    # The caller decides the initial status per request (no system default). Beyond `ready`
    # only with vulns:import.
    status: Literal["draft", "ready", "sent", "fixing", "retesting", "fixed", "risk_accepted"] = "draft"
    # Usernames of the operators to assign.
    operators: list[str] = Field(default_factory=list, max_length=20)
    # Free-form data from the tool; merged with any unknown top-level fields.
    metadata: dict[str, Any] = Field(default_factory=dict)

    # --- vulns:import only: a past vulnerability with its history ---------------------------
    internal_id: str | None = Field(default=None, max_length=32)   # its original VULN-0042
    rvs_id: str | None = Field(default=None, max_length=200)
    created_at: datetime | None = None
    ready_at: datetime | None = None
    sent_at: datetime | None = None
    accepted_at: datetime | None = None
    accepted_by: str | None = Field(default=None, max_length=150)        # username
    fixing_at: datetime | None = None
    retesting_at: datetime | None = None
    fixed_at: datetime | None = None
    risk_accepted_at: datetime | None = None
    risk_accepted_by: str | None = Field(default=None, max_length=150)   # username
    risk_reason: str | None = Field(default=None, max_length=2000)
    updated_at: datetime | None = None

    @field_validator(*DATE_FIELDS)
    @classmethod
    def _past_utc(cls, v: datetime | None, info) -> datetime | None:
        """Stored like the database's own timestamps: UTC without a zone; never in the future."""
        if v is None:
            return None
        if v.tzinfo is not None:
            v = v.astimezone(UTC).replace(tzinfo=None)
        if v > datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5):
            raise ValueError(f"{info.field_name} cannot be in the future")
        return v

    @field_validator("internal_id")
    @classmethod
    def _vuln_number(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        if not re.fullmatch(r"VULN-\d{1,9}", v.strip(), re.IGNORECASE):
            raise ValueError("internal_id must look like 'VULN-0042'")
        return v.strip().upper()

    def import_fields_used(self) -> list[str]:
        """The fields (and status) that need vulns:import, as sent."""
        used = [f for f in IMPORT_FIELDS if getattr(self, f) not in (None, "")]
        if self.status not in ("draft", "ready"):
            used.insert(0, f"status '{self.status}'")
        return used

    @field_validator("cwe")
    @classmethod
    def _normalise_cwe(cls, v: str | None) -> str | None:
        return normalise_cwe(v)

    @field_validator("references")
    @classmethod
    def _http_references(cls, refs: list[str]) -> list[str]:
        return http_references(refs)

    @model_validator(mode="after")
    def _metadata_size(self) -> "IngestVuln":
        extra = self.model_extra or {}
        size = len(json.dumps({**extra, **self.metadata}, default=str).encode())
        if size > MAX_METADATA_BYTES:
            raise ValueError(f"metadata exceeds {MAX_METADATA_BYTES // 1024} KB")
        return self

    def combined_metadata(self) -> dict[str, Any]:
        """Unknown top-level fields plus the explicit `metadata` object."""
        return {**(self.model_extra or {}), **self.metadata}


class IngestResult(BaseModel):
    id: uuid.UUID
    internal_id: str | None
    status: str
    batch_id: str | None = None
    imported: bool = False   # created with its history (vulns:import)


class BatchResult(BaseModel):
    """A new batch: send `batch_id` with each vulnerability of the run."""

    batch_id: str
    created_at: datetime
