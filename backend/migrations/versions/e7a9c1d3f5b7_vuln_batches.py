"""Vulnerability batches: vulns created together by a tool through the integration API.

Revision ID: e7a9c1d3f5b7
Revises: d5f7a9b1c3e5
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "e7a9c1d3f5b7"
down_revision: Union[str, None] = "d5f7a9b1c3e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS vuln_batch_seq START 1")
    op.create_table(
        "vuln_batches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("internal_id", sa.Text, nullable=False, unique=True),
        sa.Column("api_key_id", UUID(as_uuid=True), sa.ForeignKey("api_keys.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "vulnerabilities",
        sa.Column("batch_id", sa.Text, sa.ForeignKey("vuln_batches.internal_id"), nullable=True),
    )
    op.create_index("ix_vulnerabilities_batch_id", "vulnerabilities", ["batch_id"])


def downgrade() -> None:
    op.drop_index("ix_vulnerabilities_batch_id", table_name="vulnerabilities")
    op.drop_column("vulnerabilities", "batch_id")
    op.drop_table("vuln_batches")
    op.execute("DROP SEQUENCE IF EXISTS vuln_batch_seq")
