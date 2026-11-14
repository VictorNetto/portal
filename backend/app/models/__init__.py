"""ORM models for the Red Team Operations Platform.

Importing this package pulls in every model so SQLAlchemy's metadata and
Alembic's autogenerate see all tables. Keep new models added to the imports.
"""

from app.models.attachment import Attachment
from app.models.audit import AuditLog
from app.models.dashboard import Dashboard, DashboardLink
from app.models.enums import (
    AuditAction,
    ReportStatus,
    UserRole,
    VulnStatus,
)
from app.models.report import Report, ReportSection, report_operators
from app.models.report_template import ReportTemplate
from app.models.user import ApiKey, AuthSession, User
from app.models.vulnerability import Vulnerability, vulnerability_operators

__all__ = [
    "ApiKey",
    "Attachment",
    "AuditAction",
    "AuditLog",
    "AuthSession",
    "Dashboard",
    "DashboardLink",
    "Report",
    "ReportSection",
    "ReportStatus",
    "ReportTemplate",
    "User",
    "UserRole",
    "VulnStatus",
    "Vulnerability",
    "report_operators",
    "vulnerability_operators",
]
