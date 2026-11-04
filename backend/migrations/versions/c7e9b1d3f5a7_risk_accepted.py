"""risk_accepted status; acceptance backfilled where an RVS ID was recorded (D17)

Revision ID: c7e9b1d3f5a7
Revises: b5d7f9a1c3e6
Create Date: 2026-11-03 22:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c7e9b1d3f5a7"
down_revision: Union[str, None] = "b5d7f9a1c3e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE vuln_status ADD VALUE IF NOT EXISTS 'risk_accepted'")
    op.add_column("vulnerabilities", sa.Column("risk_accepted_at", sa.DateTime(), nullable=True))
    op.add_column("vulnerabilities", sa.Column(
        "risk_accepted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("vulnerabilities", sa.Column("risk_reason", sa.Text(), nullable=True))
    # Recording the RVS ID now implies acceptance; earlier records get it at the same moment.
    op.execute("UPDATE vulnerabilities SET accepted_at = fixing_at "
               "WHERE accepted_at IS NULL AND fixing_at IS NOT NULL")


def downgrade() -> None:
    # A value cannot be removed from a PostgreSQL enum: those vulns go back to sent.
    op.execute("UPDATE vulnerabilities SET status = 'sent' WHERE status = 'risk_accepted'")
    op.drop_column("vulnerabilities", "risk_reason")
    op.drop_column("vulnerabilities", "risk_accepted_by")
    op.drop_column("vulnerabilities", "risk_accepted_at")
