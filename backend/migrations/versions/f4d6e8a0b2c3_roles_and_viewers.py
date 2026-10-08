"""rename roles to write_all/read_all, add restricted roles and record viewers

D10: two restricted roles (write_restricted, read_restricted) and per-record
"shared with" lists used by read_restricted. Existing users keep their access:
writer_all -> write_all, reader_all -> read_all.

Revision ID: f4d6e8a0b2c3
Revises: e2b4c6d8f0a1
Create Date: 2026-10-08 10:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f4d6e8a0b2c3"
down_revision: Union[str, None] = "e2b4c6d8f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users.role and api_keys.role share the enum type, so one rename covers both.
    op.execute("ALTER TYPE user_role RENAME VALUE 'writer_all' TO 'write_all'")
    op.execute("ALTER TYPE user_role RENAME VALUE 'reader_all' TO 'read_all'")
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'write_restricted'")
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'read_restricted'")

    op.create_table(
        "vulnerability_viewers",
        sa.Column("vulnerability_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["vulnerability_id"], ["vulnerabilities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("vulnerability_id", "user_id"),
    )
    op.create_table(
        "report_viewers",
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("report_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("report_viewers")
    op.drop_table("vulnerability_viewers")
    # PostgreSQL cannot drop enum values: the restricted roles are mapped back
    # onto their closest unrestricted ones, then the type is rebuilt.
    op.execute("UPDATE users SET role = 'write_all' WHERE role = 'write_restricted'")
    op.execute("UPDATE users SET role = 'read_all' WHERE role = 'read_restricted'")
    op.execute("UPDATE api_keys SET role = 'write_all' WHERE role = 'write_restricted'")
    op.execute("UPDATE api_keys SET role = 'read_all' WHERE role = 'read_restricted'")
    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'writer_all', 'reader_all', 'auditor')")
    for table in ("users", "api_keys"):
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN role TYPE user_role USING "
            "(CASE role::text WHEN 'write_all' THEN 'writer_all' WHEN 'read_all' THEN 'reader_all' "
            "ELSE role::text END)::user_role"
        )
    op.execute("DROP TYPE user_role_old")
