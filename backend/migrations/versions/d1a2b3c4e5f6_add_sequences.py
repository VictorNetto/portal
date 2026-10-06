"""add vuln and report id sequences

Revision ID: d1a2b3c4e5f6
Revises: c6c6256ad2a0
Create Date: 2026-10-06 23:40:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "d1a2b3c4e5f6"
down_revision: Union[str, None] = "c6c6256ad2a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SPEC §15.2 — formatted as VULN-%04d / OP-%04d in the app layer.
    op.execute("CREATE SEQUENCE IF NOT EXISTS vuln_seq START 1")
    op.execute("CREATE SEQUENCE IF NOT EXISTS report_seq START 1")


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS report_seq")
    op.execute("DROP SEQUENCE IF EXISTS vuln_seq")
