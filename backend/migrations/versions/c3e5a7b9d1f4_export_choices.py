"""Which sections of a vulnerability / report go into its documents (export and send).

Revision ID: c3e5a7b9d1f4
Revises: b1d3f5a7c9e2
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "c3e5a7b9d1f4"
down_revision: Union[str, None] = "b1d3f5a7c9e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vulnerabilities", sa.Column(
        "export_hidden", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("reports", sa.Column(
        "export_hidden", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("report_sections", sa.Column(
        "exported", sa.Boolean, nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("report_sections", "exported")
    op.drop_column("reports", "export_hidden")
    op.drop_column("vulnerabilities", "export_hidden")
