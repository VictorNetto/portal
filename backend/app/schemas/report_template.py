"""Report template request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.vulnerability import OperatorRef

MAX_TEXT = 200_000  # same limit as the report's own Markdown fields


class TemplateSection(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content_markdown: str | None = Field(default=None, max_length=MAX_TEXT)


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    executive_summary_md: str | None = Field(default=None, max_length=MAX_TEXT)
    introduction_md: str | None = Field(default=None, max_length=MAX_TEXT)
    sections: list[TemplateSection] = Field(default_factory=list, max_length=50)
    # Available to every user. Only an admin may set it.
    is_global: bool = False


class TemplateUpdate(BaseModel):
    """Partial update; only the fields that are sent change.

    Editing the content (name, texts, sections) needs `version`, the one the client loaded:
    a stale version is rejected with 409 so nobody silently overwrites someone else's edit.
    `is_global` (share with everyone / stop sharing) is admin-only.
    """

    version: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    executive_summary_md: str | None = Field(default=None, max_length=MAX_TEXT)
    introduction_md: str | None = Field(default=None, max_length=MAX_TEXT)
    sections: list[TemplateSection] | None = Field(default=None, max_length=50)
    is_global: bool | None = None


class TemplateListItem(BaseModel):
    id: uuid.UUID
    name: str
    is_global: bool
    owner: OperatorRef
    mine: bool
    # May this user edit / delete it? (owner while private; admins always)
    can_edit: bool
    version: int
    section_count: int
    created_at: datetime
    updated_at: datetime


class TemplateOut(TemplateListItem):
    executive_summary_md: str | None
    introduction_md: str | None
    sections: list[TemplateSection]
