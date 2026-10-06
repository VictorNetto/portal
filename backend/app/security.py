"""Cryptographic primitives: password hashing, API-key hashing, JWT.

- User passwords: bcrypt (slow, salted) — they are low-entropy (D7).
- API keys: SHA-256 of a high-entropy random string — fast, safe because the
  key is unguessable (D7). Verified on every machine-to-machine request.
- JWTs: short-lived access tokens + longer refresh tokens (§10.1).
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.config import settings

# --- Passwords (bcrypt) ---


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


# --- API keys (SHA-256 over high-entropy input, D7) ---

API_KEY_BYTES = 32  # 256 bits of CSPRNG entropy


def generate_api_key() -> tuple[str, str, str]:
    """Return (plaintext, prefix, hash). Plaintext is shown to the admin once;
    only the prefix and hash are stored."""
    plaintext = secrets.token_urlsafe(API_KEY_BYTES)
    prefix = plaintext[:8]
    return plaintext, prefix, hash_api_key(plaintext)


def hash_api_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


# --- JWT ---

TokenType = Literal["access", "refresh"]


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    return _create_token(
        subject, "access", timedelta(minutes=settings.access_token_ttl_minutes)
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject, "refresh", timedelta(days=settings.refresh_token_ttl_days)
    )


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Decode and validate a JWT. Raises jwt.PyJWTError on any problem
    (expired, bad signature, wrong type)."""
    payload = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"expected {expected_type} token")
    return payload
