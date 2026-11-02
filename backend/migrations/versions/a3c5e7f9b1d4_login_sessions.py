"""server-side login sessions, and failed logins in the audit log (D16)

Revision ID: a3c5e7f9b1d4
Revises: f2b4d6e8a0c3
Create Date: 2026-11-02 23:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a3c5e7f9b1d4"
down_revision: Union[str, None] = "f2b4d6e8a0c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_jti", sa.Text(), nullable=False),
        sa.Column("previous_jti", sa.Text(), nullable=True),
        sa.Column("rotated_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])

    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'login_failed'")
    op.drop_constraint("ck_audit_exactly_one_actor", "audit_logs", type_="check")
    op.create_check_constraint(
        "ck_audit_actor", "audit_logs",
        "(user_id IS NULL) != (api_key_id IS NULL) OR "
        "(action::text = 'login_failed' AND api_key_id IS NULL)",
    )
    op.create_index("ix_audit_action_created", "audit_logs", ["action", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_action_created", "audit_logs")
    op.drop_constraint("ck_audit_actor", "audit_logs", type_="check")
    op.execute("DELETE FROM audit_logs WHERE user_id IS NULL AND api_key_id IS NULL")
    op.create_check_constraint(
        "ck_audit_exactly_one_actor", "audit_logs", "(user_id IS NULL) != (api_key_id IS NULL)"
    )
    op.drop_index("ix_auth_sessions_user_id", "auth_sessions")
    op.drop_table("auth_sessions")
    # A value cannot be removed from a PostgreSQL enum; 'login_failed' stays, unused.
