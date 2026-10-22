"""Report template request/response schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.report_template import ShareStatus
from app.schemas.vulnerability import OperatorRef

MAX_TEXT = 200_000  # same limit as the report's own Markdown fields


class TemplateSection(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content_markdown: str | None = Field(default=None, max_length=MAX_TEXT)


class TemplateCreate(BaseModel):
    """A new template is always private; sharing goes through a request and an admin's approval."""

    name: str = Field(min_length=1, max_length=120)
    executive_summary_md: str | None = Field(default=None, max_length=MAX_TEXT)
    introduction_md: str | None = Field(default=None, max_length=MAX_TEXT)
    sections: list[TemplateSection] = Field(default_factory=list, max_length=50)


class TemplateUpdate(BaseModel):
    """Partial content update; only the fields that are sent change. `version` is the one the
    client loaded: a stale version is rejected with 409, so nobody silently overwrites an edit."""

    version: int
    name: str | None = Field(default=None, min_length=1, max_length=120)
    executive_summary_md: str | None = Field(default=None, max_length=MAX_TEXT)
    introduction_md: str | None = Field(default=None, max_length=MAX_TEXT)
    sections: list[TemplateSection] | None = Field(default=None, max_length=50)


SharingAction = Literal["request", "withdraw", "approve", "reject", "unshare", "reshare"]


class SharingChange(BaseModel):
    """request / withdraw: the owner. approve / reject / unshare / reshare: an admin."""

    action: SharingAction


class TemplateListItem(BaseModel):
    id: uuid.UUID
    name: str
    share_status: ShareStatus
    is_global: bool            # convenience: share_status == "shared"
    owner: OperatorRef
    mine: bool
    can_edit: bool             # may this user edit / delete it right now?
    can_use: bool              # may this user start a report from it?
    actions: list[SharingAction]  # sharing steps this user may take now
    share_requested_at: datetime | None
    share_decided_at: datetime | None
    share_decided_by: OperatorRef | None
    version: int
    section_count: int
    created_at: datetime
    updated_at: datetime


class TemplateOut(TemplateListItem):
    executive_summary_md: str | None
    introduction_md: str | None
    sections: list[TemplateSection]
