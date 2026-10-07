"""API key schemas (SPEC §10.1). Plaintext is shown exactly once at creation."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import UserRole


class ApiKeyCreate(BaseModel):
    label: str = Field(min_length=1, max_length=150)
    role: UserRole
    expires_at: datetime | None = None


class ApiKeyOut(BaseModel):
    """Listing/metadata view — never includes the plaintext."""

    id: uuid.UUID
    label: str
    key_prefix: str
    role: UserRole
    expires_at: datetime | None
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreated(ApiKeyOut):
    """Returned once on creation — carries the plaintext key."""

    plaintext: str
