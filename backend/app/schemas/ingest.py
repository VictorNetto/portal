"""Inbound (machine) vulnerability payload — SPEC §11.

Required-ness depends on the requested initial status (see services/ingest.py):
a `draft` only needs *something* meaningful, while `saved_local` needs the same
fields the UI demands before "Enviar". Unknown top-level fields are accepted and
kept as extra metadata, so scanners can send their own data without us having
to model it.
"""

import json
import re
import uuid
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_METADATA_BYTES = 64 * 1024


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

    # The caller decides the initial status per request (no system default).
    status: Literal["draft", "saved_local"] = "draft"
    # Usernames of the operators to assign.
    operators: list[str] = Field(default_factory=list, max_length=20)
    # Free-form data from the tool; merged with any unknown top-level fields.
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("cwe")
    @classmethod
    def _normalise_cwe(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        m = re.fullmatch(r"(?:CWE-)?(\d{1,6})", v.strip(), re.IGNORECASE)
        if not m:
            raise ValueError("cwe must look like 'CWE-79' (or just '79')")
        return f"CWE-{m.group(1)}"

    @field_validator("references")
    @classmethod
    def _http_references(cls, refs: list[str]) -> list[str]:
        cleaned = [r.strip() for r in refs if r and r.strip()]
        for r in cleaned:
            if not re.fullmatch(r"https?://\S{1,2000}", r, re.IGNORECASE):
                raise ValueError(f"reference is not an http(s) URL: {r[:60]}")
        return cleaned

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
