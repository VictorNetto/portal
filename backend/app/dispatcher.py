"""Dispatcher service — the single decoupled egress point (SPEC §12).

Callers use `dispatch(target, payload)` and know nothing about the transport.
Today the only implementation is a no-op stub that records that a dispatch
occurred (email/ServiceNow drop in later by implementing Transport and swapping
the module-level `transport` — callers are unchanged).
"""

from dataclasses import dataclass, field
from typing import Protocol

from app.config import settings


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


# The active transport. Swapped here (or via config) when a real one exists.
transport: Transport = StubTransport()


def dispatch(target: str, payload: DispatchPayload) -> DispatchResult:
    """Single egress call. Insulates callers from the transport (§12)."""
    return transport.send(target, payload)
