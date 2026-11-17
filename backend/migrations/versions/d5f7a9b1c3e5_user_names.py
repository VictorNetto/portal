"""A user's full name and display name (not the login).

Revision ID: d5f7a9b1c3e5
Revises: c3e5a7b9d1f4
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5f7a9b1c3e5"
down_revision: Union[str, None] = "c3e5a7b9d1f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.Text, nullable=True))
    op.add_column("users", sa.Column("display_name", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("users", "display_name")
    op.drop_column("users", "full_name")
