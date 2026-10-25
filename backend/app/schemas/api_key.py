"""API key schemas (SPEC §10.1). Plaintext is shown exactly once at creation."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Scope = Literal["vulns:read", "vulns:write", "rvs:write", "reports:read", "exports"]  # app/scopes.py


class ApiKeyCreate(BaseModel):
    label: str = Field(min_length=1, max_length=150)
    scopes: list[Scope] = Field(min_length=1)
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def _unique(cls, v: list[str]) -> list[str]:
        return sorted(set(v))


class ApiKeyOut(BaseModel):
    """Listing/metadata view — never includes the plaintext."""

    id: uuid.UUID
    label: str
    key_prefix: str
    scopes: list[str]
    expires_at: datetime | None
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreated(ApiKeyOut):
    """Returned once on creation — carries the plaintext key."""

    plaintext: str
