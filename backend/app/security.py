"""Cryptographic primitives: password hashing, API-key hashing, JWT.

- User passwords: bcrypt (slow, salted) — they are low-entropy (D7).
- API keys: SHA-256 of a high-entropy random string — fast, safe because the
  key is unguessable (D7). Verified on every machine-to-machine request.
- JWTs: short-lived access tokens + refresh tokens bounded by the session (§10.1, D12),
  tied to a server-side session so they can be revoked (D16).
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.config import settings

# --- Passwords (bcrypt) ---


PASSWORD_MAX_BYTES = 72  # bcrypt refuses anything longer


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


_dummy_hash: str | None = None


def verify_password_or_nothing(plain: str, hashed: str | None) -> bool:
    """Spend the same time when there is no account, so timing doesn't reveal which
    usernames exist."""
    global _dummy_hash
    if hashed is None:
        _dummy_hash = _dummy_hash or hash_password(secrets.token_urlsafe(16))
        verify_password(plain, _dummy_hash)
        return False
    return verify_password(plain, hashed)


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


def new_token_id() -> str:
    return secrets.token_urlsafe(9)


def _create_token(
    subject: str, token_type: TokenType, started: datetime, exp: datetime, sid: str,
    jti: str | None = None,
) -> str:
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": datetime.now(UTC),
        "jti": jti or new_token_id(),  # every token differs, even within one second
        "sid": sid,  # the server-side session (auth_sessions)
        "sst": int(started.timestamp()),  # session start: never moves on refresh
        "exp": exp,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def session_end(started: datetime) -> datetime:
    return started + timedelta(minutes=settings.session_max_minutes)


def create_session_tokens(
    subject: str, sid: str, refresh_jti: str, started: datetime | None = None
) -> tuple[str, str, datetime]:
    """Return (access, refresh, session end) for a session that began at
    `started` (now, for a login). Neither token outlives the session; the
    refresh token also dies after the idle window unless it is renewed."""
    now = datetime.now(UTC)
    started = started or now.replace(microsecond=0)  # the token stores whole seconds
    end = session_end(started)
    access_exp = min(now + timedelta(minutes=settings.access_token_ttl_minutes), end)
    refresh_exp = min(now + timedelta(minutes=settings.session_idle_minutes), end)
    return (
        _create_token(subject, "access", started, access_exp, sid),
        _create_token(subject, "refresh", started, refresh_exp, sid, refresh_jti),
        end,
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
