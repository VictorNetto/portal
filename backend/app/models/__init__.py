"""ORM models for the Red Team Operations Platform.

Importing this package pulls in every model so SQLAlchemy's metadata and
Alembic's autogenerate see all tables. Keep new models added to the imports.
"""

from app.models.enums import (
    AuditAction,
    ReportStatus,
    UserRole,
    VulnStatus,
)
from app.models.user import ApiKey, User
from app.models.report import Report, ReportSection, report_operators
from app.models.vulnerability import Vulnerability, vulnerability_operators
from app.models.attachment import Attachment
from app.models.audit import AuditLog

__all__ = [
    "AuditAction",
    "ReportStatus",
    "UserRole",
    "VulnStatus",
    "User",
    "ApiKey",
    "Report",
    "ReportSection",
    "report_operators",
    "Vulnerability",
    "vulnerability_operators",
    "Attachment",
    "AuditLog",
]
