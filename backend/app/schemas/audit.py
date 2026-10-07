"""Audit log viewer schemas (SPEC §10.3)."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AuditAction


class AuditEntry(BaseModel):
    id: int
    actor: str  # username, "api:<prefix>", or "system"
    action: AuditAction
    entity_type: str | None
    entity_id: uuid.UUID | None
    detail: dict | None
    ip_address: str | None
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditEntry]
    total: int
    page: int
    page_size: int
