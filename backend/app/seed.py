"""First-run admin seed (SPEC §10.1).

On startup, if no users exist, create one admin. Use the configured password
if given; otherwise generate a strong random one and print it to stdout exactly
once (never stored in plaintext). The admin must change it on first login.
"""

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import security
from app.config import settings
from app.models.enums import UserRole
from app.models.user import User


def seed_first_admin(session: Session) -> None:
    existing = session.scalar(select(User.id).limit(1))
    if existing is not None:
        return  # users already exist; nothing to do

    password = settings.first_admin_password or secrets.token_urlsafe(16)
    admin = User(
        username=settings.first_admin_username,
        password_hash=security.hash_password(password),
        role=UserRole.admin,
        must_change_password=True,
    )
    session.add(admin)
    session.commit()

    if settings.first_admin_password is None:
        # Printed once to container stdout; grab via `docker compose logs api`.
        print(
            "\n" + "=" * 60,
            f"  FIRST-RUN ADMIN CREATED",
            f"  username: {settings.first_admin_username}",
            f"  password: {password}",
            f"  (change it on first login — shown only once)",
            "=" * 60 + "\n",
            sep="\n",
            flush=True,
        )
