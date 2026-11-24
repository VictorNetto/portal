"""Imported vulnerabilities: when a past vuln was brought in with its history (vulns:import).

Revision ID: f9b1d3e5a7c9
Revises: e7a9c1d3f5b7
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f9b1d3e5a7c9"
down_revision: Union[str, None] = "e7a9c1d3f5b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vulnerabilities", sa.Column("imported_at", sa.DateTime, nullable=True))


def downgrade() -> None:
    op.drop_column("vulnerabilities", "imported_at")
