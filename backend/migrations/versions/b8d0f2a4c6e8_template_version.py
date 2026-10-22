"""report_templates.version (optimistic concurrency for template edits)

Revision ID: b8d0f2a4c6e8
Revises: a7c9e1b3d5f7
Create Date: 2026-10-22 16:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8d0f2a4c6e8"
down_revision: Union[str, None] = "a7c9e1b3d5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "report_templates",
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("report_templates", "version")
