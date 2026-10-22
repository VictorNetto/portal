"""report templates

Reusable text for a report's sections (executive summary, introduction, free-form
sections). Reports remember which template they were created from.

Revision ID: a7c9e1b3d5f7
Revises: f4d6e8a0b2c3
Create Date: 2026-10-22 10:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7c9e1b3d5f7"
down_revision: Union[str, None] = "f4d6e8a0b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_global", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("executive_summary_md", sa.Text(), nullable=True),
        sa.Column("introduction_md", sa.Text(), nullable=True),
        sa.Column("sections", postgresql.JSONB(astext_type=sa.Text()),
                  server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_templates_owner", "report_templates", ["owner_id"])
    op.add_column(
        "reports",
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "reports_template_id_fkey", "reports", "report_templates",
        ["template_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("reports_template_id_fkey", "reports", type_="foreignkey")
    op.drop_column("reports", "template_id")
    op.drop_index("ix_report_templates_owner", table_name="report_templates")
    op.drop_table("report_templates")
