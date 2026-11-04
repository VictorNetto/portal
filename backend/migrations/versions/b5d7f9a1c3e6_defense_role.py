"""defense-team role, and acceptance of sent vulns (D17)

Revision ID: b5d7f9a1c3e6
Revises: a3c5e7f9b1d4
Create Date: 2026-11-03 10:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b5d7f9a1c3e6"
down_revision: Union[str, None] = "a3c5e7f9b1d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'defense'")
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'accept'")
    op.add_column("vulnerabilities", sa.Column("accepted_at", sa.DateTime(), nullable=True))
    op.add_column("vulnerabilities", sa.Column(
        "accepted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("vulnerabilities", "accepted_by")
    op.drop_column("vulnerabilities", "accepted_at")
    # PostgreSQL cannot drop enum values: defense accounts are deactivated as read-only
    # restricted users, and 'defense' / 'accept' stay in their types, unused.
    op.execute("UPDATE users SET role = 'read_restricted', is_active = false WHERE role = 'defense'")
