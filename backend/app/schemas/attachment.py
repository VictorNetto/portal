"""Attachment schemas (SPEC §5.1, §15.10)."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class AttachmentOut(BaseModel):
    id: uuid.UUID
    vulnerability_id: uuid.UUID | None
    original_filename: str
    display_name: str | None
    mime_type: str
    size_bytes: int
    is_image: bool
    created_at: datetime

    model_config = {"from_attributes": True}
