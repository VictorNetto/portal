"""Enumerations — the canonical set from SPEC §15.1.

These are stored as native PostgreSQL ENUM types (see each model's column
definitions). Python `str`-based enums so values serialize cleanly to JSON/API.
"""

import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    write_all = "write_all"
    read_all = "read_all"
    auditor = "auditor"
    # Restricted roles (D10): see/touch only records they created, operate or were shared.
    write_restricted = "write_restricted"
    read_restricted = "read_restricted"
    # D17: the defense team. Reads sent vulns only, accepts them and records their RVS ID.
    defense = "defense"


class VulnStatus(str, enum.Enum):
    """D14. draft -complete-> ready -send-> sent -RVS ID-> fixing <-> retesting -> fixed"""
    draft = "draft"          # Rascunho
    ready = "ready"          # Pronta
    sent = "sent"            # Enviada
    fixing = "fixing"        # Em correção
    retesting = "retesting"  # Em reteste
    fixed = "fixed"          # Corrigida


class ReportStatus(str, enum.Enum):
    """D14. A send in progress or failed is `reports.sending`, not a status."""
    draft = "draft"  # Rascunho
    sent = "sent"    # Enviado


class AuditAction(str, enum.Enum):
    login = "login"
    login_failed = "login_failed"  # D16: the only entry that may have no actor
    logout = "logout"
    create = "create"
    read = "read"
    update = "update"
    delete = "delete"
    status_change = "status_change"
    export = "export"
    send = "send"
    api_key_create = "api_key_create"
    api_key_revoke = "api_key_revoke"
    permission_change = "permission_change"
    lock_override = "lock_override"  # D4
    correction = "correction"  # D6
    accept = "accept"  # D17: the defense team took a sent vuln
