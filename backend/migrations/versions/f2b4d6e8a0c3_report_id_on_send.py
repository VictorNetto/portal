"""reports get their internal ID when they are sent (D15)

Draft reports lose the number they got at creation; the sequence simply moves on.
A report frozen by a failed send keeps its number, because it was assigned for that send.

Revision ID: f2b4d6e8a0c3
Revises: e1a3c5d7f9b2
Create Date: 2026-11-02 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "f2b4d6e8a0c3"
down_revision: Union[str, None] = "e1a3c5d7f9b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE reports SET internal_id = NULL WHERE status = 'draft' AND NOT sending")


def downgrade() -> None:
    op.execute("UPDATE reports SET internal_id = 'OP-' || lpad(nextval('report_seq')::text, 4, '0') "
               "WHERE internal_id IS NULL")
