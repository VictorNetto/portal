"""vulnerabilities and reports move to the six-status model (D14)

Vulnerabilities: draft, ready, sent, fixing, retesting, fixed. `acknowledged` merges into
`fixing`, and a vulnerability caught mid-send goes back to draft (its report stays frozen).
Reports: draft, sent. A send in progress or failed is now the `sending` flag, not a status.
The audit action `dispatch` becomes `send`. Past audit details keep the words of their time.

Revision ID: e1a3c5d7f9b2
Revises: d0f2b4c6e8a1
Create Date: 2026-11-02 18:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1a3c5d7f9b2"
down_revision: Union[str, None] = "d0f2b4c6e8a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _retype(table: str, name: str, values: tuple[str, ...], case: str) -> None:
    labels = ", ".join(f"'{v}'" for v in values)
    op.execute(f"CREATE TYPE {name}_new AS ENUM ({labels})")
    op.execute(f"ALTER TABLE {table} ALTER COLUMN status DROP DEFAULT")
    op.execute(f"ALTER TABLE {table} ALTER COLUMN status TYPE {name}_new "
               f"USING (CASE status::text {case} ELSE status::text END)::{name}_new")
    op.execute(f"ALTER TABLE {table} ALTER COLUMN status SET DEFAULT 'draft'")
    op.execute(f"DROP TYPE {name}")
    op.execute(f"ALTER TYPE {name}_new RENAME TO {name}")


def upgrade() -> None:
    op.drop_index("ix_vulns_status_dispatched_at", table_name="vulnerabilities")

    op.alter_column("vulnerabilities", "saved_local_at", new_column_name="ready_at")
    op.alter_column("vulnerabilities", "dispatched_at", new_column_name="sent_at")
    op.alter_column("vulnerabilities", "waiting_fix_at", new_column_name="fixing_at")
    op.alter_column("vulnerabilities", "pending_retest_at", new_column_name="retesting_at")
    # The fix starts when the RVS ID is recorded.
    op.execute("UPDATE vulnerabilities SET fixing_at = acknowledged_at WHERE acknowledged_at IS NOT NULL")
    op.drop_column("vulnerabilities", "acknowledged_at")

    op.alter_column("reports", "dispatched_at", new_column_name="sent_at")
    op.alter_column("reports", "dispatch_error", new_column_name="send_error")
    op.add_column("reports", sa.Column("sending", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.execute("UPDATE reports SET sending = true WHERE status = 'dispatching'")

    _retype("vulnerabilities", "vuln_status", ("draft", "ready", "sent", "fixing", "retesting", "fixed"),
            "WHEN 'saved_local' THEN 'ready' WHEN 'dispatching' THEN 'draft' WHEN 'dispatched' THEN 'sent' "
            "WHEN 'acknowledged' THEN 'fixing' WHEN 'waiting_fix' THEN 'fixing' "
            "WHEN 'pending_retest' THEN 'retesting'")
    _retype("reports", "report_status", ("draft", "sent"),
            "WHEN 'dispatching' THEN 'draft' WHEN 'dispatched' THEN 'sent'")
    op.execute("ALTER TYPE audit_action RENAME VALUE 'dispatch' TO 'send'")

    op.create_index("ix_vulns_status_sent_at", "vulnerabilities", ["status", "sent_at"])


def downgrade() -> None:
    op.drop_index("ix_vulns_status_sent_at", table_name="vulnerabilities")
    op.execute("ALTER TYPE audit_action RENAME VALUE 'send' TO 'dispatch'")

    _retype("reports", "report_status", ("draft", "dispatching", "dispatched"), "WHEN 'sent' THEN 'dispatched'")
    op.execute("UPDATE reports SET status = 'dispatching' WHERE sending")
    _retype("vulnerabilities", "vuln_status",
            ("draft", "saved_local", "dispatching", "dispatched", "acknowledged", "waiting_fix",
             "pending_retest", "fixed"),
            "WHEN 'ready' THEN 'saved_local' WHEN 'sent' THEN 'dispatched' WHEN 'fixing' THEN 'waiting_fix' "
            "WHEN 'retesting' THEN 'pending_retest'")

    op.drop_column("reports", "sending")
    op.alter_column("reports", "send_error", new_column_name="dispatch_error")
    op.alter_column("reports", "sent_at", new_column_name="dispatched_at")

    op.add_column("vulnerabilities", sa.Column("acknowledged_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE vulnerabilities SET acknowledged_at = fixing_at")
    op.alter_column("vulnerabilities", "retesting_at", new_column_name="pending_retest_at")
    op.alter_column("vulnerabilities", "fixing_at", new_column_name="waiting_fix_at")
    op.alter_column("vulnerabilities", "sent_at", new_column_name="dispatched_at")
    op.alter_column("vulnerabilities", "ready_at", new_column_name="saved_local_at")

    op.create_index("ix_vulns_status_dispatched_at", "vulnerabilities", ["status", "dispatched_at"])
