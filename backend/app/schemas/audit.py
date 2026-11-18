"""Audit log viewer schemas (SPEC §10.3)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import AuditAction, UserRole


class AuditEntry(BaseModel):
    id: int
    actor: str  # username, "api:<prefix>", the name typed on a failed login, or "system"
    actor_name: str | None = None   # the person's display/full name, when it differs from `actor`
    action: AuditAction
    entity_type: str | None
    entity_id: uuid.UUID | None
    entity_label: str | None = None  # VULN-0001 / the report's id, a user's login, a template's name…
    detail: dict | None
    ip_address: str | None
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditEntry]
    total: int
    page: int
    page_size: int


# --- search (the filter bar: same grammar as the Hub, parsed in the browser) -------------

TextKey = Literal["text", "actor", "record", "ip", "detail"]


class AuditFilter(BaseModel):
    """One filter token. `negate` turns it into "not this".

    - action / role / entity: `values` (any of them; entity "none" = no entity)
    - text / actor / record / ip / detail: `text` (contains, case-insensitive; record = a VULN/report
      internal id or a uuid, and also matches the record's attachments)
    - date: `from_` / `to` (UTC instants; either may be missing; `to` exclusive)
    """

    key: Literal["action", "role", "entity", "date"] | TextKey
    negate: bool = False
    values: list[str] = Field(default_factory=list, max_length=50)
    text: str | None = Field(default=None, max_length=300)
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _check(self):
        if self.key == "action":
            valid = {a.value for a in AuditAction}
            if not self.values or any(v not in valid for v in self.values):
                raise ValueError("unknown action")
        elif self.key == "role":
            valid = {r.value for r in UserRole}
            if not self.values or any(v not in valid for v in self.values):
                raise ValueError("unknown role")
        elif self.key == "entity":
            if not self.values:
                raise ValueError("entity needs a value")
        elif self.key == "date":
            if self.from_ is None and self.to is None:
                raise ValueError("date needs from and/or to")
        elif not (self.text or "").strip():
            raise ValueError(f"{self.key} needs a text")
        return self


class AuditSearch(BaseModel):
    filters: list[AuditFilter] = Field(default_factory=list, max_length=30)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=200)


class AuditFacets(BaseModel):
    """Values for the filter menus."""

    actors: list[str]
    entity_types: list[str]
