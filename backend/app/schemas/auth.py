"""Auth request/response schemas."""

import uuid

from pydantic import BaseModel

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CurrentUser(BaseModel):
    """The authenticated user, as returned by /auth/me and injected into routes."""

    id: uuid.UUID
    username: str
    role: UserRole
    must_change_password: bool

    model_config = {"from_attributes": True}
