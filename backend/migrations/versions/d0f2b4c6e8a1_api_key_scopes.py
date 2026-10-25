"""API keys carry scopes instead of a user role (D13)

Keys whose role could create vulnerabilities (admin, write_all) keep exactly that
ability (`vulns:write`); the others could do nothing, so they get no scope.

Revision ID: d0f2b4c6e8a1
Revises: c9e1a3b5d7f9
Create Date: 2026-10-25 18:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d0f2b4c6e8a1"
down_revision: Union[str, None] = "c9e1a3b5d7f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column(
        "scopes", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False))
    op.execute("UPDATE api_keys SET scopes = ARRAY['vulns:write'] WHERE role IN ('admin', 'write_all')")
    op.drop_column("api_keys", "role")


def downgrade() -> None:
    op.add_column("api_keys", sa.Column(
        "role", postgresql.ENUM(name="user_role", create_type=False), nullable=True))
    op.execute("UPDATE api_keys SET role = CASE WHEN 'vulns:write' = ANY(scopes) "
               "THEN 'write_all'::user_role ELSE 'read_all'::user_role END")
    op.alter_column("api_keys", "role", nullable=False)
    op.drop_column("api_keys", "scopes")
