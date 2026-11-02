"""Report dispatch (two phases, D2) and the dispatcher."""

import pytest
from conftest import new_report, png_bytes, report_vuln, tag, upload
from sqlalchemy import select

from app import dispatcher
from app.db import SessionLocal
from app.models.enums import ReportStatus, VulnStatus
from app.models.report import Report
from app.models.user import User
from app.models.vulnerability import Vulnerability
from app.schemas.report import ReportCreate
from app.schemas.vulnerability import VulnCreate
from app.services import report as report_svc
from app.services import report_dispatch


def build_report(c, *, blank_identifier=False):
    rid = new_report(c, client_name="ACME")["id"]
    low = report_vuln(c, rid, cvss_score=3.0, description="baixa")
    high = report_vuln(c, rid, cvss_score=9.5, description="alta")
    extra = c.post(f"/reports/{rid}/vulnerabilities", {"description": "sem identificador"}).json() if blank_identifier else None
    return rid, low, high, extra


def test_dispatch_needs_the_lock(writer, writer2):
    rid, *_ = build_report(writer)
    assert writer2.post(f"/reports/{rid}/send").status_code == 409


def test_every_vuln_needs_an_identifier(writer):
    rid, *_rest, extra = build_report(writer, blank_identifier=True)
    r = writer.post(f"/reports/{rid}/send")
    assert r.status_code == 422 and "identifier" in r.json()["detail"]
    assert writer.get(f"/reports/{rid}").json()["status"] == "draft"          # nothing changed
    writer.patch(f"/vulnerabilities/{extra['id']}", {"version": extra["version"], "identifier": f"pytest-{tag()}"})
    assert writer.post(f"/reports/{rid}/send").status_code == 200


def test_dispatch_releases_the_vulns_in_severity_order(writer, reader):
    rid, low, high, _ = build_report(writer)
    r = writer.post(f"/reports/{rid}/send")
    assert r.status_code == 200
    rep = r.json()
    assert rep["internal_id"].startswith("OP-")                                # numbered on send
    assert rep["status"] == "sent" and rep["sent_at"] and rep["lock"] is None and rep["send_error"] is None
    vulns = {v["id"]: v for v in rep["vulnerabilities"]}
    assert all(v["status"] == "sent" and v["internal_id"].startswith("VULN-") and v["sent_at"] for v in vulns.values())
    n = lambda v: int(v["internal_id"].split("-")[1])
    assert n(vulns[high["id"]]) < n(vulns[low["id"]])                          # high severity first

    # they now live in the normal list and the RVS queue, and follow the normal lifecycle
    listed = [x["id"] for x in reader.get("/vulnerabilities").json()]
    queued = [x["id"] for x in reader.get("/rvs-queue").json()]
    assert high["id"] in listed and high["id"] in queued
    ack = writer.post(f"/vulnerabilities/{high['id']}/rvs", {"rvs_id": "RVS-pytest-9"})
    assert ack.status_code == 200 and ack.json()["status"] == "fixing"
    move = lambda to: writer.post(f"/vulnerabilities/{high['id']}/transition", {"to": to})
    assert move("retesting").status_code == 200                    # released: it moves on its own
    assert move("fixed").status_code == 200


def test_report_progress_counts_its_fixed_vulnerabilities(writer):
    rid, low, high, _ = build_report(writer)
    rep = writer.post(f"/reports/{rid}/send").json()
    assert (rep["vuln_count"], rep["fixed_count"]) == (2, 0)
    for v in (low, high):
        writer.post(f"/vulnerabilities/{v['id']}/rvs", {"rvs_id": f"RVS-pytest-{tag()}"})
        writer.post(f"/vulnerabilities/{v['id']}/transition", {"to": "retesting"})
        writer.post(f"/vulnerabilities/{v['id']}/transition", {"to": "fixed"})
    rep = writer.get(f"/reports/{rid}").json()
    assert rep["status"] == "sent" and (rep["vuln_count"], rep["fixed_count"]) == (2, 2)
    listed = next(r for r in writer.get("/reports").json() if r["id"] == rid)
    assert listed["fixed_count"] == 2


def test_a_sent_report_is_immutable_except_internal_notes(writer, writer2):
    rid, *_ = build_report(writer)
    writer.post(f"/reports/{rid}/send")
    assert writer.post(f"/reports/{rid}/send").status_code == 409          # not twice
    assert writer.patch(f"/reports/{rid}", {"name": "renamed"}).status_code == 422
    notes = writer2.patch(f"/reports/{rid}", {"internal_notes": "ok without a lock"})   # any writer, no lock needed
    assert notes.status_code == 200 and notes.json()["internal_notes"] == "ok without a lock"
    assert writer.post(f"/reports/{rid}/lock").status_code == 409
    assert writer.post(f"/reports/{rid}/sections", {"title": "x"}).status_code == 409
    assert writer.delete(f"/reports/{rid}").status_code == 409                 # D1
    assert upload(writer, f"/reports/{rid}/attachments", "a.pdf", b"%PDF-1.4 x").status_code == 409


def test_dispatch_is_audited_in_both_phases(admin, writer):
    rid, *_ = build_report(writer)
    writer.post(f"/reports/{rid}/send")
    items = admin.get("/audit-logs", params={"action": "send", "page_size": 200}).json()["items"]
    phases = {e["detail"].get("phase") for e in items if e["entity_id"] == rid}
    assert phases == {1, 2}


class FlakyTransport:
    name = "flaky"

    def __init__(self):
        self.fail, self.sent, self.last = True, 0, None

    def send(self, target, payload):
        if self.fail:
            return dispatcher.DispatchResult(ok=False, transport=self.name, detail="SMTP unreachable")
        self.sent += 1
        self.last = payload
        return dispatcher.DispatchResult(ok=True, transport=self.name)


def test_failed_delivery_leaves_a_frozen_draft_and_retry_does_not_reissue_ids():
    flaky = FlakyTransport()
    original, dispatcher.transport = dispatcher.transport, flaky
    try:
        with SessionLocal() as s:
            admin = s.scalar(select(User).where(User.username == "admin"))
            report = report_svc.create(s, ReportCreate(name=f"pytest-fail-{tag()}"), admin, None)
            rid = report.id
            report_svc.create_vuln(s, rid, VulnCreate(identifier=f"pytest-{tag()}", cvss_score=8, description="d"), admin, None)
            report_svc.create_vuln(s, rid, VulnCreate(identifier=f"pytest-{tag()}", cvss_score=2, description="d"), admin, None)

            from fastapi import HTTPException

            with pytest.raises(HTTPException) as err:
                report_dispatch.send(s, rid, admin, None)
            assert err.value.status_code == 502

            s.expire_all()
            rep = s.get(Report, rid)
            vulns = list(s.scalars(select(Vulnerability).where(Vulnerability.report_id == rid)))
            # Phase 1 is committed; nothing is labelled "sent" (D2), and the report is frozen.
            assert rep.status == ReportStatus.draft and rep.sending and "SMTP unreachable" in rep.send_error
            assert all(v.status == VulnStatus.draft and v.internal_id for v in vulns)
            assert rep.sent_at is None and all(v.sent_at is None for v in vulns)
            ids = sorted(v.internal_id for v in vulns)
            number = rep.internal_id
            assert number.startswith("OP-")

            flaky.fail = False                                  # the operator retries the same call
            out = report_dispatch.send(s, rid, admin, None)
            s.expire_all()
            assert out.status == ReportStatus.sent and s.get(Report, rid).send_error is None and not s.get(Report, rid).sending
            vulns = list(s.scalars(select(Vulnerability).where(Vulnerability.report_id == rid)))
            assert all(v.status == VulnStatus.sent for v in vulns)
            assert sorted(v.internal_id for v in vulns) == ids       # not re-issued
            assert s.get(Report, rid).internal_id == number
            assert flaky.sent == 1                                   # delivered exactly once
            names = [n for n, _ in flaky.last.attachments]
            assert any(n.endswith(".pdf") for n in names) and any(n.endswith(".xlsx") for n in names)
    finally:
        dispatcher.transport = original


def test_the_package_carries_non_image_files_but_not_images(writer):
    rid, low, high, _ = build_report(writer)
    upload(writer, f"/vulnerabilities/{high['id']}/attachments", "log.txt", b"request log")
    upload(writer, f"/vulnerabilities/{high['id']}/attachments", "shot.png", png_bytes())
    upload(writer, f"/reports/{rid}/attachments", "evidence.pdf", b"%PDF-1.4 e")

    seen = {}

    class Capture:
        name = "capture"

        def send(self, target, payload):
            seen["names"] = [n for n, _ in payload.attachments]
            return dispatcher.DispatchResult(ok=True, transport="capture")

    # Run the real dispatch in-process so the transport can be observed.
    original, dispatcher.transport = dispatcher.transport, Capture()
    try:
        with SessionLocal() as s:
            admin = s.scalar(select(User).where(User.username == writer.user["username"]))
            report_dispatch.send(s, __import__("uuid").UUID(rid), admin, None)
    finally:
        dispatcher.transport = original
    names = seen["names"]
    assert any(n.endswith(".pdf") and "evidence" not in n for n in names)           # the report PDF
    assert any(n.endswith(".xlsx") for n in names)
    assert any("log.txt" in n for n in names) and any("evidence.pdf" in n for n in names)
    assert not any(n.endswith(".png") for n in names)                                # images travel inside the PDF


def test_smtp_transport_degrades_gracefully():
    from app.config import settings

    t = dispatcher.SmtpTransport()
    payload = dispatcher.DispatchPayload(subject="s", body="b", attachments=[("a.txt", b"x")])
    saved = (settings.smtp_host, settings.smtp_from, settings.dispatch_to, settings.smtp_port, settings.smtp_starttls)
    try:
        settings.smtp_host = settings.smtp_from = settings.dispatch_to = ""
        r = t.send("blue-team", payload)
        assert not r.ok and "SMTP_HOST" in r.detail and "DISPATCH_TO" in r.detail
        settings.smtp_host, settings.smtp_from, settings.dispatch_to = "127.0.0.1", "p@x.test", "b@x.test"
        settings.smtp_port, settings.smtp_starttls = 1, False
        r = t.send("blue-team", payload)
        assert not r.ok and "ConnectionRefusedError" in r.detail          # reported, never raised
    finally:
        settings.smtp_host, settings.smtp_from, settings.dispatch_to, settings.smtp_port, settings.smtp_starttls = saved


def test_a_report_that_cannot_render_stays_an_editable_draft(writer, monkeypatch):
    rep = new_report(writer, name="pytest-render-" + tag())
    report_vuln(writer, rep["id"], identifier="x")
    with SessionLocal() as s:
        user = s.scalar(select(User).where(User.username == writer.user["username"]))
        r = s.get(Report, rep["id"])

        def broken(*_a, **_k):
            raise ValueError("boom")

        monkeypatch.setattr(report_dispatch, "build_package", broken)
        with pytest.raises(Exception) as caught:
            report_dispatch.send(s, r.id, user, None)
        assert caught.value.status_code == 422
        s.rollback()
        s.expire_all()
        r = s.get(Report, rep["id"])
        assert r.status == ReportStatus.draft and not r.sending and r.internal_id is None


def test_a_frozen_report_that_cannot_render_is_unfrozen(writer, monkeypatch):
    rep = new_report(writer, name="pytest-thaw-" + tag())
    report_vuln(writer, rep["id"], identifier="x")
    with SessionLocal() as s:
        user = s.scalar(select(User).where(User.username == writer.user["username"]))
        r = s.get(Report, rep["id"])
        r.sending, r.internal_id = True, "OP-T" + tag()
        s.commit()

        def broken(*_a, **_k):
            raise ValueError("boom")

        monkeypatch.setattr(report_dispatch, "build_package", broken)
        with pytest.raises(Exception) as caught:
            report_dispatch.send(s, r.id, user, None)
        assert caught.value.status_code == 422
        s.expire_all()
        assert not s.get(Report, rep["id"]).sending
