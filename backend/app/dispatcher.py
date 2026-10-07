"""Dispatcher service — the single decoupled egress point (SPEC §12).

Callers use `dispatch(target, payload)` and know nothing about the transport.
Two implementations: a no-op stub (default) and SMTP email, chosen by
`DISPATCH_TRANSPORT`. ServiceNow or anything else drops in by implementing
Transport — callers are unchanged.
"""

import mimetypes
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

from app.config import settings

# The slim image's MIME table lacks Office types; mail clients rely on the right one.
mimetypes.add_type("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx")


@dataclass
class DispatchPayload:
    """What gets sent. Rendered artifacts are opaque bytes to the transport."""

    subject: str
    body: str
    attachments: list[tuple[str, bytes]] = field(default_factory=list)  # (filename, data)


@dataclass
class DispatchResult:
    ok: bool
    transport: str
    detail: str | None = None


class Transport(Protocol):
    name: str

    def send(self, target: str, payload: DispatchPayload) -> DispatchResult: ...


class StubTransport:
    """No-op transport for MVP/dev: logs the intent, never actually sends.
    Replace with SmtpTransport (SMTP) or a ServiceNow transport later."""

    name = "stub"

    def send(self, target: str, payload: DispatchPayload) -> DispatchResult:
        print(
            f"[dispatcher:stub] would send to {target!r}: "
            f"subject={payload.subject!r} attachments={len(payload.attachments)}",
            flush=True,
        )
        return DispatchResult(ok=True, transport=self.name, detail="stub: not actually sent")


class SmtpTransport:
    """Sends the package as one email (plain-text body + every file attached).

    Never raises: any failure comes back as ok=False with a short reason, so the
    caller can keep the record in `dispatching` and let the operator retry (D2).
    Credentials are never included in the returned detail.
    """

    name = "smtp"

    def _recipients(self) -> list[str]:
        return [r.strip() for r in settings.dispatch_to.split(",") if r.strip()]

    def send(self, target: str, payload: DispatchPayload) -> DispatchResult:
        recipients = self._recipients()
        missing = [
            name for name, value in (
                ("SMTP_HOST", settings.smtp_host), ("SMTP_FROM", settings.smtp_from),
                ("DISPATCH_TO", recipients),
            ) if not value
        ]
        if missing:
            return DispatchResult(ok=False, transport=self.name,
                                  detail="SMTP is not configured: " + ", ".join(missing))

        msg = EmailMessage()
        msg["Subject"] = payload.subject
        msg["From"] = settings.smtp_from
        msg["To"] = ", ".join(recipients)
        msg.set_content(payload.body)
        for filename, data in payload.attachments:
            ctype, _ = mimetypes.guess_type(filename)
            maintype, _, subtype = (ctype or "application/octet-stream").partition("/")
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

        try:
            if settings.smtp_ssl:
                server = smtplib.SMTP_SSL(
                    settings.smtp_host, settings.smtp_port,
                    timeout=settings.smtp_timeout_seconds, context=ssl.create_default_context(),
                )
            else:
                server = smtplib.SMTP(
                    settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
                )
            with server:
                if settings.smtp_starttls and not settings.smtp_ssl:
                    server.starttls(context=ssl.create_default_context())
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                refused = server.send_message(msg)
            if refused:
                return DispatchResult(ok=False, transport=self.name,
                                      detail="recipients refused: " + ", ".join(refused))
        except Exception as exc:  # noqa: BLE001 - report every failure, never raise
            return DispatchResult(ok=False, transport=self.name,
                                  detail=f"{type(exc).__name__}: {str(exc)[:200]}")
        return DispatchResult(ok=True, transport=self.name,
                              detail=f"sent to {len(recipients)} recipient(s)")


def _build_transport() -> Transport:
    if settings.dispatch_transport == "smtp":
        return SmtpTransport()
    return StubTransport()


# The active transport, chosen by DISPATCH_TRANSPORT.
transport: Transport = _build_transport()


def dispatch(target: str, payload: DispatchPayload) -> DispatchResult:
    """Single egress call. Insulates callers from the transport (§12)."""
    return transport.send(target, payload)
