"""add vulnerabilities.saved_local_at

Records when a vuln was sent (draft -> saved_local) so the lifecycle timeline
is complete. Existing rows are backfilled from the audit log.

Revision ID: e2b4c6d8f0a1
Revises: d1a2b3c4e5f6
Create Date: 2026-10-07 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2b4c6d8f0a1"
down_revision: Union[str, None] = "d1a2b3c4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vulnerabilities", sa.Column("saved_local_at", sa.DateTime(), nullable=True))
    # The send transition was always audited as status_change {"to": "saved_local"}.
    op.execute(
        """
        UPDATE vulnerabilities v
        SET saved_local_at = a.at
        FROM (
            SELECT entity_id, min(created_at) AS at
            FROM audit_logs
            WHERE entity_type = 'vulnerability'
              AND action = 'status_change'
              AND detail->>'to' = 'saved_local'
            GROUP BY entity_id
        ) a
        WHERE v.id = a.entity_id
        """
    )


def downgrade() -> None:
    op.drop_column("vulnerabilities", "saved_local_at")
