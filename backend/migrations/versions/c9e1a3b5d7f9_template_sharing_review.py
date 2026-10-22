"""template sharing goes through an admin review

Replaces report_templates.is_global with a share status:
private -> pending (owner asks) -> shared (admin approves); an admin may unshare (unshared)
and share again. Templates that were global become `shared`.

Revision ID: c9e1a3b5d7f9
Revises: b8d0f2a4c6e8
Create Date: 2026-10-22 18:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c9e1a3b5d7f9"
down_revision: Union[str, None] = "b8d0f2a4c6e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATUS = postgresql.ENUM("private", "pending", "shared", "unshared", name="template_share_status")


def upgrade() -> None:
    STATUS.create(op.get_bind(), checkfirst=True)
    op.add_column("report_templates", sa.Column(
        "share_status", STATUS, server_default="private", nullable=False))
    op.add_column("report_templates", sa.Column("share_requested_at", sa.DateTime(), nullable=True))
    op.add_column("report_templates", sa.Column("share_decided_at", sa.DateTime(), nullable=True))
    op.add_column("report_templates", sa.Column(
        "share_decided_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "report_templates_share_decided_by_fkey", "report_templates", "users",
        ["share_decided_by"], ["id"],
    )
    op.execute("UPDATE report_templates SET share_status = 'shared', share_decided_at = updated_at "
               "WHERE is_global")
    op.drop_column("report_templates", "is_global")
    op.create_index("ix_report_templates_share_status", "report_templates", ["share_status"])


def downgrade() -> None:
    op.add_column("report_templates", sa.Column(
        "is_global", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.execute("UPDATE report_templates SET is_global = (share_status = 'shared')")
    op.drop_index("ix_report_templates_share_status", table_name="report_templates")
    op.drop_constraint("report_templates_share_decided_by_fkey", "report_templates", type_="foreignkey")
    for col in ("share_decided_by", "share_decided_at", "share_requested_at", "share_status"):
        op.drop_column("report_templates", col)
    STATUS.drop(op.get_bind(), checkfirst=True)
