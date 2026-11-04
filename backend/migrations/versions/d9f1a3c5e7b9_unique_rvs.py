"""each RVS ID belongs to one vulnerability (D17)

Unique among live vulns, ignoring case and surrounding spaces. A deleted vuln, or one whose
RVS ID an admin correction removed, frees its ID.

Revision ID: d9f1a3c5e7b9
Revises: c7e9b1d3f5a7
Create Date: 2026-11-04 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "d9f1a3c5e7b9"
down_revision: Union[str, None] = "c7e9b1d3f5a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dupes = op.get_bind().execute(text(
        "SELECT lower(btrim(rvs_id)) FROM vulnerabilities "
        "WHERE rvs_id IS NOT NULL AND deleted_at IS NULL GROUP BY 1 HAVING count(*) > 1"
    )).scalars().all()
    if dupes:  # stop rather than guess which vuln keeps the ID
        raise RuntimeError(f"RVS IDs used by more than one vulnerability: {', '.join(dupes)}")
    op.execute(
        "CREATE UNIQUE INDEX uq_vulnerabilities_rvs_id ON vulnerabilities (lower(btrim(rvs_id))) "
        "WHERE rvs_id IS NOT NULL AND deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_vulnerabilities_rvs_id")
