"""Enumerations — the canonical set from SPEC §15.1.

These are stored as native PostgreSQL ENUM types (see each model's column
definitions). Python `str`-based enums so values serialize cleanly to JSON/API.
"""

import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    writer_all = "writer_all"
    reader_all = "reader_all"
    auditor = "auditor"


class VulnStatus(str, enum.Enum):
    draft = "draft"
    saved_local = "saved_local"
    dispatching = "dispatching"  # transient (D2): render + send in progress
    dispatched = "dispatched"
    acknowledged = "acknowledged"
    waiting_fix = "waiting_fix"
    pending_retest = "pending_retest"
    fixed = "fixed"


class ReportStatus(str, enum.Enum):
    draft = "draft"
    dispatching = "dispatching"  # transient (D2)
    dispatched = "dispatched"


class AuditAction(str, enum.Enum):
    login = "login"
    logout = "logout"
    create = "create"
    read = "read"
    update = "update"
    delete = "delete"
    status_change = "status_change"
    export = "export"
    dispatch = "dispatch"
    api_key_create = "api_key_create"
    api_key_revoke = "api_key_revoke"
    permission_change = "permission_change"
    lock_override = "lock_override"  # D4
    correction = "correction"  # D6
