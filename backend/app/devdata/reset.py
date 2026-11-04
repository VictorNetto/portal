"""Wipe the development database and fill it with a realistic data set.

    docker compose exec -T api python -m app.devdata.reset --yes

Keeps the admin account (and its password) and the migrations. Every other user, record,
attachment, API key and audit entry is removed, and the internal-ID counters restart.
Team accounts use their username as password. Refuses to run outside development.
"""

import io
import random
import sys
import uuid
from datetime import datetime, timedelta
from string import Template

from PIL import Image, ImageDraw
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import security
from app.config import settings
from app.db import SessionLocal
from app.devdata import content as c
from app.models.attachment import Attachment
from app.models.audit import AuditLog
from app.models.enums import AuditAction, ReportStatus, UserRole, VulnStatus
from app.models.report import Report, ReportSection
from app.models.report_template import ReportTemplate, ShareStatus
from app.models.user import User
from app.models.vulnerability import Vulnerability
from app.seed import seed_first_admin
from app.services.report_lock import utcnow
from app.storage import get_storage

# username, role, active, must change password
TEAM = [
    ("benjamin", UserRole.write_restricted, True, False),
    ("danielle", UserRole.read_restricted, True, False),
    ("isabella", UserRole.read_all, True, False),
    ("jonathan", UserRole.write_all, True, False),
    ("kimberly", UserRole.write_all, False, False),
    ("madeline", UserRole.read_all, True, True),
    ("michelle", UserRole.write_all, True, False),
    ("nicholas", UserRole.read_restricted, True, False),
    ("samantha", UserRole.write_restricted, True, False),
    ("theodore", UserRole.write_restricted, True, False),
    ("victoria", UserRole.auditor, True, False),
    ("defesa", UserRole.defense, True, False),
]
OPERATORS = ["jonathan", "michelle", "benjamin", "samantha", "theodore"]
ORDER = list(VulnStatus)
WIPED = ("audit_logs, attachments, api_keys, report_sections, report_operators, report_viewers, "
         "vulnerability_operators, vulnerability_viewers, vulnerabilities, reports, report_templates")


def wipe(session: Session) -> None:
    storage = get_storage()
    for key in session.scalars(select(Attachment.s3_key)):
        storage.delete(key)
    session.execute(text(f"TRUNCATE {WIPED}"))
    session.execute(text("DELETE FROM users WHERE username <> :admin"),
                    {"admin": settings.first_admin_username})
    session.execute(text("ALTER SEQUENCE vuln_seq RESTART WITH 1"))
    session.execute(text("ALTER SEQUENCE report_seq RESTART WITH 1"))
    session.commit()


def team(session: Session) -> dict[str, User]:
    seed_first_admin(session)
    users = {}
    for name, role, active, must_change in TEAM:
        users[name] = User(username=name, password_hash=security.hash_password(name), role=role,
                           is_active=active, must_change_password=must_change)
        session.add(users[name])
    session.flush()
    return users


def fill(blocks: list[str], **values) -> str:
    return "\n\n".join(Template(b).safe_substitute(values) for b in blocks)


def evidence_png(label: str) -> bytes:
    """A neutral illustrative image, so embedded evidence and exports have something to show."""
    image = Image.new("RGB", (900, 320), "#f4f6f8")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 880, 300), outline="#d8dde4", width=2)
    draw.text((50, 130), "Evidência ilustrativa", fill="#27323f", font_size=28)
    draw.text((50, 175), label[:80], fill="#5f6d7e", font_size=16)
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


class Builder:
    def __init__(self, session: Session, users: dict[str, User]):
        self.s, self.users = session, users
        self.rng = random.Random(20261102)
        self.now = utcnow().replace(microsecond=0)
        self.topic = 0
        self.vuln_n = self.report_n = self.rvs_n = 0

    def ago(self, days: float) -> datetime:
        return self.now - timedelta(days=days, minutes=self.rng.randint(0, 600))

    def audit(self, actor: User, action: AuditAction, kind: str, entity, at, **detail) -> None:
        self.s.add(AuditLog(user_id=actor.id, action=action, entity_type=kind, entity_id=entity,
                            detail=detail or None, ip_address="10.20.30.40", created_at=at))

    def attach(self, actor: User, at, *, vuln=None, report=None, name, mime, data, image) -> uuid.UUID:
        att_id = uuid.uuid4()
        key = f"devdata/{att_id}"
        get_storage().put(key, io.BytesIO(data), len(data), mime)
        self.s.add(Attachment(id=att_id, vulnerability_id=vuln, report_id=report, s3_key=key,
                              original_filename=name, display_name=name, mime_type=mime,
                              size_bytes=len(data), is_image=image, uploaded_by=actor.id, created_at=at))
        return att_id

    def vuln(self, app, client, environment, status, created, sent, report=None, operators=(), final=None):
        """`sent` is when it left the Red Team; `final` the upper bound of its later dates."""
        topic, cwe = c.TOPICS[self.topic % len(c.TOPICS)]
        self.topic += 1
        vector, score = self.rng.choice(c.SEVERITIES)
        actor = operators[0]
        values = dict(app=app, topic=topic.lower(), client=client, environment=environment)
        vid = uuid.uuid4()
        v = Vulnerability(
            id=vid, report_id=report, status=status, identifier=f"{topic} em {app}", cwe=cwe,
            description=fill(c.DESCRIPTION, **values), finding_detail=fill(c.DETAIL, **values),
            mitigation=fill(c.MITIGATION, **values), references=c.REFERENCES, cvss_score=score,
            cvss_vector=vector, source="Red Team", internal_notes=self.rng.choice(c.NOTES),
            created_by=actor.id, created_at=created, updated_at=created,
        )
        v.operators = list(operators)
        self.audit(actor, AuditAction.create, "vulnerability", vid, created)
        return v, final or self.now

    def advance(self, v, sent, final, actor) -> None:
        """Walk a sent vulnerability through its dates up to its status."""
        if v.status == VulnStatus.risk_accepted:  # the defense team chose not to fix it
            v.sent_at = sent
            v.risk_accepted_at = v.updated_at = sent + (final - sent) * self.rng.uniform(0.1, 0.6)
            v.risk_accepted_by = self.users["defesa"].id
            v.risk_reason = self.rng.choice(c.RISK_REASONS)
            self.audit(self.users["defesa"], AuditAction.status_change, "vulnerability", v.id,
                       v.risk_accepted_at, to="risk_accepted")
            return
        steps = ORDER[ORDER.index(VulnStatus.sent):ORDER.index(v.status) + 1]
        moments = sorted(sent + (final - sent) * self.rng.uniform(0.1, 0.95) for _ in steps[1:])
        at = v.sent_at = sent
        for step, at in zip(steps[1:], moments, strict=True):
            setattr(v, f"{step.value}_at", at)
            self.audit(actor, AuditAction.status_change, "vulnerability", v.id, at, to=step.value)
        if v.status not in (VulnStatus.draft, VulnStatus.ready, VulnStatus.sent):
            self.rvs_n += 1
            v.rvs_id = f"RVS-2026-{self.rvs_n:05d}"
        # The defense team accepts before it records the RVS ID; some sent ones are still new.
        if v.fixing_at or (v.status == VulnStatus.sent and self.rng.random() < 0.5):
            v.accepted_at = sent + ((v.fixing_at or final) - sent) * self.rng.uniform(0.2, 0.8)
            v.accepted_by = self.users["defesa"].id
            self.audit(self.users["defesa"], AuditAction.accept, "vulnerability", v.id, v.accepted_at)
        v.updated_at = at

    def number_vuln(self) -> str:
        return self.s.execute(text("SELECT nextval('vuln_seq')")).scalar_one()

    def embed(self, v, actor, at) -> None:
        att = self.attach(actor, at, vuln=v.id, name="evidencia.png", mime="image/png",
                          data=evidence_png(v.identifier), image=True)
        v.finding_detail += f"\n\n## Evidência\n\n![evidencia.png](/api/attachments/{att}/content)"

    def report(self, spec: dict) -> None:
        sent_days = spec["sent"]
        end = self.now - timedelta(days=(sent_days or 1) + 3)
        start = end - timedelta(days=spec["days"])
        created = start - timedelta(days=2)
        operators = [self.users[n] for n in self.rng.sample(OPERATORS, 3)]
        actor = operators[0]
        count = len(spec["statuses"])
        rid = uuid.uuid4()
        rep = Report(
            id=rid, name=spec["name"], client_name=spec["client"], start_date=start.date(), end_date=end.date(),
            test_type=spec["test_type"], test_model=spec["test_model"], environment=spec["environment"],
            demand_origin=spec["origin"], scope=f"{spec['app']}, conforme termo de autorização do projeto.",
            created_by=actor.id, created_at=created, updated_at=created,
            status=ReportStatus.sent if sent_days else ReportStatus.draft,
        )
        rep.operators = operators
        self.s.add(rep)
        self.s.flush()
        for i, (title, body) in enumerate(c.SECTIONS, 1):
            self.s.add(ReportSection(report_id=rid, position=i, title=title, content_markdown=body))

        sent = self.ago(sent_days) if sent_days else None
        vulns = []
        for status in spec["statuses"]:
            v, _ = self.vuln(spec["app"], spec["client"], spec["environment"], VulnStatus(status),
                             start + timedelta(days=self.rng.uniform(0, spec["days"])), sent,
                             report=rid, operators=self.rng.sample(operators, 2))
            vulns.append(v)
        self.s.add_all(vulns)
        self.s.flush()

        high = sum(1 for v in vulns if v.cvss_score >= 7)
        values = dict(client=spec["client"], app=spec["app"], start=f"{start:%d/%m/%Y}", end=f"{end:%d/%m/%Y}",
                      count=count, high=high)
        rep.executive_summary_md = fill(c.EXECUTIVE, **values)
        rep.introduction_md = fill(c.INTRODUCTION, **values)
        rep.updated_at = end
        self.attach(actor, end, report=rid, name="escopo.csv", mime="text/csv", image=False,
                    data=f"sistema,area\n{spec['app']},{spec['client']}\n".encode())

        vulns.sort(key=lambda v: -v.cvss_score)  # numbers follow severity, as on a real send
        for i, v in enumerate(vulns):
            if i % 2 == 0:
                self.embed(v, actor, end)
            if sent or spec.get("failed_send"):
                v.internal_id = f"VULN-{self.number_vuln():04d}"
            if sent:
                self.advance(v, sent, self.now, actor)
        if sent or spec.get("failed_send"):
            n = self.s.execute(text("SELECT nextval('report_seq')")).scalar_one()
            rep.internal_id = f"OP-{n:04d}"
        if sent:
            rep.sent_at = rep.updated_at = sent
            self.audit(actor, AuditAction.send, "report", rid, sent, phase=2, ok=True)
        if spec.get("failed_send"):
            rep.sending, rep.send_error = True, "SMTP unreachable"

    def standalone(self) -> None:
        for app, status, days in c.STANDALONE:
            operators = [self.users[n] for n in self.rng.sample(OPERATORS, 2)]
            actor = operators[0]
            status = VulnStatus(status)
            created = self.ago(days)
            v, _ = self.vuln(app, "Time de Produto", "production", status, created, None, operators=operators)
            self.s.add(v)
            self.s.flush()
            if status != VulnStatus.draft:
                v.internal_id = f"VULN-{self.number_vuln():04d}"
                v.ready_at = v.updated_at = created + timedelta(hours=4)
            if status not in (VulnStatus.draft, VulnStatus.ready):
                self.advance(v, created + timedelta(days=1), self.now, actor)
            self.embed(v, actor, created)
            if status == VulnStatus.sent:
                v.viewers = [self.users["danielle"], self.users["nicholas"]]

    def templates(self) -> None:
        owner = self.users["jonathan"]
        for name, share in c.TEMPLATES:
            self.s.add(ReportTemplate(
                name=name, owner_id=owner.id, share_status=ShareStatus(share),
                executive_summary_md=fill(c.EXECUTIVE, client="[cliente]", app="[sistema]", start="[início]",
                                          end="[fim]", count="[n]", high="[n]"),
                introduction_md=fill(c.INTRODUCTION, client="[cliente]", app="[sistema]"),
                sections=[{"title": t, "content_markdown": b} for t, b in c.SECTIONS],
                share_requested_at=self.now if share == "pending" else None,
            ))


def main() -> int:
    if settings.environment != "development":
        print(f"Refusing to run: ENVIRONMENT is {settings.environment!r}, not 'development'.")
        return 1
    if "--yes" not in sys.argv:
        print("This erases the database. Run again with --yes to continue.")
        return 1
    with SessionLocal() as session:
        wipe(session)
        builder = Builder(session, team(session))
        builder.templates()
        session.flush()
        for spec in sorted(c.REPORTS, key=lambda r: -(r["sent"] or 0)):
            builder.report(spec)
        builder.standalone()
        session.commit()
        rows = session.execute(text(
            "SELECT (SELECT count(*) FROM users), (SELECT count(*) FROM reports), "
            "(SELECT count(*) FROM vulnerabilities), (SELECT count(*) FROM attachments)")).one()
    print("users={} reports={} vulnerabilities={} attachments={}".format(*rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
