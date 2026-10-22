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
    """Admin only, for now: make a template available to everyone (or not)."""

    is_global: bool


class TemplateListItem(BaseModel):
    id: uuid.UUID
    name: str
    is_global: bool
    owner: OperatorRef
    mine: bool
    section_count: int
    created_at: datetime
    updated_at: datetime


class TemplateOut(TemplateListItem):
    executive_summary_md: str | None
    introduction_md: str | None
    sections: list[TemplateSection]
