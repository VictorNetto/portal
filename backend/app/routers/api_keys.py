"""API key management (SPEC §10.1). Admin-only.

Keys are high-entropy random strings hashed with SHA-256 (D7). The plaintext is
returned exactly once at creation and never stored.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit, security
from app.db import get_session
from app.deps import require_roles
from app.models.enums import AuditAction, UserRole
from app.models.user import ApiKey, User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyOut

router = APIRouter(prefix="/api-keys", tags=["api-keys"])
_admin = require_roles(UserRole.admin)


@router.get("", response_model=list[ApiKeyOut])
def list_keys(
    _: User = Depends(_admin),
    session: Session = Depends(get_session),
) -> list:
    return list(session.scalars(select(ApiKey).order_by(ApiKey.created_at.desc())))


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_key(
    body: ApiKeyCreate,
    request: Request,
    admin: User = Depends(_admin),
    session: Session = Depends(get_session),
) -> ApiKeyCreated:
    plaintext, prefix, key_hash = security.generate_api_key()
    key = ApiKey(
        label=body.label,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=body.scopes,
        created_by=admin.id,
        expires_at=body.expires_at,
    )
    session.add(key)
    session.flush()
    audit.record(
        session, action=AuditAction.api_key_create, user_id=admin.id,
        entity_type="api_key", entity_id=key.id,
        detail={"label": key.label, "scopes": key.scopes}, request=request,
    )
    session.commit()
    session.refresh(key)
    # Build the response from the metadata view, then inject the one-time plaintext.
    base = ApiKeyOut.model_validate(key, from_attributes=True)
    return ApiKeyCreated(**base.model_dump(), plaintext=plaintext)


@router.post("/{key_id}/revoke", response_model=ApiKeyOut)
def revoke_key(
    key_id: uuid.UUID,
    request: Request,
    admin: User = Depends(_admin),
    session: Session = Depends(get_session),
) -> ApiKeyOut:
    key = session.get(ApiKey, key_id)
    if key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    if key.revoked_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "API key already revoked")
    key.revoked_at = datetime.now(UTC)
    audit.record(
        session, action=AuditAction.api_key_revoke, user_id=admin.id,
        entity_type="api_key", entity_id=key.id, detail={"label": key.label},
        request=request,
    )
    session.commit()
    session.refresh(key)
    return key
