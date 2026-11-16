"""Linking existing vulnerabilities to a draft report and unlinking them; mitigation optional."""

from conftest import fixing_vuln, make_user, new_report, new_vuln, report_vuln, saved_vuln


def test_a_vuln_can_be_completed_without_mitigation(writer):
    v = new_vuln(writer, mitigation=None)
    r = writer.post(f"/vulnerabilities/{v['id']}/complete")
    assert r.status_code == 200 and r.json()["status"] == "ready"


def test_linking_brings_draft_and_ready_vulns_into_the_report(writer):
    rep = new_report(writer)
    draft = new_vuln(writer)
    ready = saved_vuln(writer)
    r = writer.post(f"/reports/{rep['id']}/vulnerabilities/link", {"ids": [draft["id"], ready["id"]]})
    assert r.status_code == 200, r.text
    assert {v["id"] for v in r.json()["vulnerabilities"]} == {draft["id"], ready["id"]}
    back = writer.get(f"/vulnerabilities/{ready['id']}").json()
    # Inside a report a vuln is a draft sent with the report; its number stays.
    assert back["report_id"] == rep["id"] and back["status"] == "draft"
    assert back["internal_id"] == ready["internal_id"]


def test_linking_needs_the_report_lock_and_a_draft_report(writer, writer2):
    rep = new_report(writer)
    v = new_vuln(writer2)
    assert writer2.post(f"/reports/{rep['id']}/vulnerabilities/link", {"ids": [v["id"]]}).status_code == 409
    sent = new_report(writer)
    report_vuln(writer, sent["id"])
    assert writer.post(f"/reports/{sent['id']}/send").status_code == 200
    assert writer.post(f"/reports/{sent['id']}/vulnerabilities/link", {"ids": [v["id"]]}).status_code == 409


def test_sent_vulns_and_vulns_of_another_report_cannot_be_linked(writer):
    rep = new_report(writer)
    sent = fixing_vuln(writer)
    assert writer.post(f"/reports/{rep['id']}/vulnerabilities/link", {"ids": [sent["id"]]}).status_code == 409
    other = new_report(writer)
    inside = report_vuln(writer, other["id"])
    assert writer.post(f"/reports/{rep['id']}/vulnerabilities/link", {"ids": [inside["id"]]}).status_code == 409
    # All or nothing: one bad id links none.
    ok = new_vuln(writer)
    assert writer.post(f"/reports/{rep['id']}/vulnerabilities/link", {"ids": [ok["id"], sent["id"]]}).status_code == 409
    assert writer.get(f"/vulnerabilities/{ok['id']}").json()["report_id"] is None


def test_unlinking_makes_it_a_standalone_draft_again(writer):
    rep = new_report(writer)
    v = report_vuln(writer, rep["id"])
    r = writer.post(f"/reports/{rep['id']}/vulnerabilities/{v['id']}/unlink")
    assert r.status_code == 200 and r.json()["vulnerabilities"] == []
    back = writer.get(f"/vulnerabilities/{v['id']}").json()
    assert back["report_id"] is None and back["status"] == "draft"
    # Now it is edited on its own, without the report's lock.
    assert writer.patch(f"/vulnerabilities/{v['id']}", {"version": back["version"], "cwe": "CWE-79"}).status_code == 200
    # Unlinking a vuln that is not in the report is a 404.
    assert writer.post(f"/reports/{rep['id']}/vulnerabilities/{v['id']}/unlink").status_code == 404


def test_unlinking_needs_the_lock(writer, writer2):
    rep = new_report(writer)
    v = report_vuln(writer, rep["id"])
    assert writer2.post(f"/reports/{rep['id']}/vulnerabilities/{v['id']}/unlink").status_code == 409


def test_a_restricted_writer_may_not_unlink_what_it_reaches_only_through_the_report(admin, writer):
    rw = make_user(admin, "write_restricted")
    rep = new_report(rw)
    mine = report_vuln(rw, rep["id"])
    theirs = new_vuln(writer)
    # writer (write_all) links its own vuln into rw's report: rw must hold the lock, so rw hands it over.
    assert rw.delete(f"/reports/{rep['id']}/lock").status_code == 204
    assert writer.post(f"/reports/{rep['id']}/lock").status_code == 200
    assert writer.post(f"/reports/{rep['id']}/vulnerabilities/link", {"ids": [theirs["id"]]}).status_code == 200
    assert writer.delete(f"/reports/{rep['id']}/lock").status_code == 204
    assert rw.post(f"/reports/{rep['id']}/lock").status_code == 200
    assert rw.post(f"/reports/{rep['id']}/vulnerabilities/{theirs['id']}/unlink").status_code == 403
    assert rw.post(f"/reports/{rep['id']}/vulnerabilities/{mine['id']}/unlink").status_code == 200
    # Nor link someone else's standalone vuln (it cannot even see it).
    other = new_vuln(writer)
    assert rw.post(f"/reports/{rep['id']}/vulnerabilities/link", {"ids": [other["id"]]}).status_code == 404


def test_link_and_unlink_are_audited(admin, writer):
    rep = new_report(writer)
    v = new_vuln(writer)
    writer.post(f"/reports/{rep['id']}/vulnerabilities/link", {"ids": [v["id"]]})
    writer.post(f"/reports/{rep['id']}/vulnerabilities/{v['id']}/unlink")
    items = admin.get("/audit-logs", params={"page_size": 200}).json()["items"]
    details = [e["detail"] or {} for e in items if e["entity_id"] == v["id"]]
    assert any("linked_to_report" in d for d in details) and any("unlinked_from_report" in d for d in details)
