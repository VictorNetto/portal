"""dashboard screens and intervals (D18)

Revision ID: b1d3f5a7c9e2
Revises: a9c1e3f5b7d9
Create Date: 2026-11-14 10:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b1d3f5a7c9e2"
down_revision: Union[str, None] = "a9c1e3f5b7d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("dashboards", sa.Column(
        "screens", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.add_column("dashboards", sa.Column("refresh_seconds", sa.Integer(), server_default="60", nullable=False))
    op.add_column("dashboards", sa.Column("rotate_seconds", sa.Integer(), server_default="30", nullable=False))
    # Every dashboard so far had one list of charts: it becomes its single screen.
    op.execute("UPDATE dashboards SET screens = jsonb_build_array(jsonb_build_object('title', NULL, 'charts', charts))")
    op.drop_column("dashboards", "charts")


def downgrade() -> None:
    op.add_column("dashboards", sa.Column(
        "charts", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False))
    # Screens are joined back into one list, in order.
    op.execute("""UPDATE dashboards SET charts = coalesce((
        SELECT jsonb_agg(c ORDER BY s.n, c.n) FROM jsonb_array_elements(screens) WITH ORDINALITY s(v, n),
        jsonb_array_elements(s.v->'charts') WITH ORDINALITY c(c, n)), '[]'::jsonb)""")
    op.drop_column("dashboards", "rotate_seconds")
    op.drop_column("dashboards", "refresh_seconds")
    op.drop_column("dashboards", "screens")
