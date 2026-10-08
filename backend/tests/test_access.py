"""Restricted roles (D10): what write_restricted / read_restricted may see and change."""

import pytest
from conftest import make_user, new_report, new_vuln, png_bytes, report_vuln, saved_vuln, tag, upload


@pytest.fixture(scope="module")
def rw(admin):  # write_restricted
    return make_user(admin, "write_restricted")


@pytest.fixture(scope="module")
def rw2(admin):
    return make_user(admin, "write_restricted")


@pytest.fixture(scope="module")
def rr(admin):  # read_restricted
    return make_user(admin, "read_restricted")


def ids(c, path="/vulnerabilities"):
    return {v["id"] for v in c.get(path).json()}


def test_restricted_writer_sees_only_what_it_created_or_operates(writer, rw, rw2):
    own = new_vuln(rw)
    assigned = new_vuln(writer, operator_ids=[rw.user["id"]])
    foreign = new_vuln(writer)
    seen = ids(rw)
    assert own["id"] in seen and assigned["id"] in seen and foreign["id"] not in seen
    # the unrestricted roles still see everything
    assert {own["id"], assigned["id"], foreign["id"]} <= ids(writer)
    # a record it cannot read does not exist for it: 404, never 403
    assert rw.get(f"/vulnerabilities/{foreign['id']}").status_code == 404
    assert rw.patch(f"/vulnerabilities/{foreign['id']}", {"version": 1, "description": "x"}).status_code == 404
    assert rw.delete(f"/vulnerabilities/{foreign['id']}").status_code == 404
    assert rw2.get(f"/vulnerabilities/{own['id']}").status_code == 404


def test_restricted_writer_edits_only_where_operator_and_deletes_only_own(writer, rw):
    mine = new_vuln(rw)
    shared_in = new_vuln(writer, operator_ids=[rw.user["id"]])
    r = rw.patch(f"/vulnerabilities/{mine['id']}", {"version": mine["version"], "description": "changed"})
    assert r.status_code == 200
    r = rw.patch(f"/vulnerabilities/{shared_in['id']}", {"version": shared_in["version"], "description": "by operator"})
    assert r.status_code == 200
    # operating is not owning: it cannot delete what someone else created
    assert rw.delete(f"/vulnerabilities/{shared_in['id']}").status_code == 403
    assert rw.delete(f"/vulnerabilities/{mine['id']}").status_code == 204


def test_read_restricted_reads_only_what_is_shared_and_never_writes(writer, rr):
    hidden = new_vuln(writer)
    shown = new_vuln(writer, viewer_ids=[rr.user["id"]])
    operated = new_vuln(writer, operator_ids=[rr.user["id"]])
    seen = ids(rr)
    assert shown["id"] in seen and operated["id"] in seen and hidden["id"] not in seen
    assert rr.get(f"/vulnerabilities/{hidden['id']}").status_code == 404
    assert rr.get(f"/vulnerabilities/{shown['id']}").status_code == 200
    assert rr.get(f"/vulnerabilities/{shown['id']}/export?format=pdf").status_code == 200
    assert rr.get(f"/vulnerabilities/{hidden['id']}/export?format=pdf").status_code == 404
    # even on a record it operates, a reader cannot change anything or create
    assert rr.patch(f"/vulnerabilities/{operated['id']}", {"version": 1, "description": "x"}).status_code == 403
    assert rr.post("/vulnerabilities", {"identifier": f"pytest-{tag()}"}).status_code == 403
    assert rr.delete(f"/vulnerabilities/{shown['id']}").status_code == 403
    assert rr.post("/vulnerabilities/export", {"ids": [hidden["id"]], "format": "xlsx"}).status_code == 404


def test_sharing_can_be_changed_by_editors_and_takes_effect_at_once(writer, rr):
    v = new_vuln(writer)
    assert rr.get(f"/vulnerabilities/{v['id']}").status_code == 404
    r = writer.patch(f"/vulnerabilities/{v['id']}", {"version": v["version"], "viewer_ids": [rr.user["id"]]})
    assert r.status_code == 200 and [x["id"] for x in r.json()["viewers"]] == [rr.user["id"]]
    assert rr.get(f"/vulnerabilities/{v['id']}").status_code == 200
    r = writer.patch(f"/vulnerabilities/{v['id']}", {"version": r.json()["version"], "viewer_ids": []})
    assert r.status_code == 200
    assert rr.get(f"/vulnerabilities/{v['id']}").status_code == 404
    assert writer.patch(f"/vulnerabilities/{v['id']}", {"version": 99, "viewer_ids": [rr.user["id"]]}).status_code == 409


def test_attachments_follow_the_record(writer, rw, rr):
    v = new_vuln(writer, viewer_ids=[rr.user["id"]])
    up = upload(writer, f"/vulnerabilities/{v['id']}/attachments", "a.png", png_bytes())
    assert up.status_code == 201
    att = up.json()["id"]
    assert rr.get(f"/vulnerabilities/{v['id']}/attachments").status_code == 200
    assert rr.get(f"/attachments/{att}/content").status_code == 200
    assert rw.get(f"/vulnerabilities/{v['id']}/attachments").status_code == 404
    assert rw.get(f"/attachments/{att}/content").status_code == 404
    assert upload(rr, f"/vulnerabilities/{v['id']}/attachments", "b.png", png_bytes()).status_code == 403


def test_rvs_queue_is_filtered_and_lifecycle_needs_write_access(writer, rw):
    mine = saved_vuln(rw)
    other = saved_vuln(writer)
    assert rw.post(f"/vulnerabilities/{mine['id']}/dispatch").status_code == 200
    assert writer.post(f"/vulnerabilities/{other['id']}/dispatch").status_code == 200
    queue = {v["id"] for v in rw.get("/rvs-queue").json()}
    assert mine["id"] in queue and other["id"] not in queue
    # a restricted writer cannot move someone else's record along
    assert rw.post(f"/vulnerabilities/{other['id']}/rvs", {"rvs_id": "RVS-x"}).status_code == 404


def test_reports_follow_the_same_rules(writer, rw, rw2, rr):
    mine = new_report(rw)
    shared = new_report(writer, viewer_ids=[rr.user["id"]])
    operated = new_report(writer, operator_ids=[rw.user["id"]])
    hidden = new_report(writer)
    for r in (shared, operated, hidden):
        writer.delete(f"/reports/{r['id']}/lock")

    assert {mine["id"], operated["id"]} <= ids(rw, "/reports")
    assert not ({shared["id"], hidden["id"]} & ids(rw, "/reports"))
    assert shared["id"] in ids(rr, "/reports") and hidden["id"] not in ids(rr, "/reports")
    assert rw.get(f"/reports/{hidden['id']}").status_code == 404
    assert rr.get(f"/reports/{hidden['id']}").status_code == 404
    assert rw2.get(f"/reports/{mine['id']}").status_code == 404

    # an operator edits through the lock, but only the creator deletes
    assert rw.post(f"/reports/{operated['id']}/lock").status_code == 200
    assert rw.patch(f"/reports/{operated['id']}", {"name": f"pytest-{tag()}"}).status_code == 200
    rw.delete(f"/reports/{operated['id']}/lock")
    assert rw.delete(f"/reports/{operated['id']}").status_code == 403
    assert rw.delete(f"/reports/{mine['id']}").status_code == 204

    # a reader reads but cannot lock or change
    assert rr.get(f"/reports/{shared['id']}").status_code == 200
    assert rr.post(f"/reports/{shared['id']}/lock").status_code == 403
    assert rr.patch(f"/reports/{shared['id']}", {"name": "x"}).status_code == 403
    assert rr.get(f"/reports/{shared['id']}/export?format=pdf").status_code == 200
    assert rr.get(f"/reports/{hidden['id']}/export?format=pdf").status_code == 404


def test_report_vulnerabilities_follow_the_report(writer, rw, rr):
    rep = new_report(writer, viewer_ids=[rr.user["id"]], operator_ids=[rw.user["id"]])
    v = report_vuln(writer, rep["id"])
    assert rr.get(f"/vulnerabilities/{v['id']}").status_code == 200
    assert rw.get(f"/vulnerabilities/{v['id']}").status_code == 200
    outsider = new_report(writer)
    hidden_v = report_vuln(writer, outsider["id"])
    assert rr.get(f"/vulnerabilities/{hidden_v['id']}").status_code == 404
    assert rw.get(f"/vulnerabilities/{hidden_v['id']}").status_code == 404
    # a restricted writer operating the report edits its vulns under the lock
    writer.delete(f"/reports/{rep['id']}/lock")
    assert rw.post(f"/reports/{rep['id']}/lock").status_code == 200
    r = rw.patch(f"/vulnerabilities/{v['id']}", {"version": v["version"], "description": "by report operator"})
    assert r.status_code == 200
    assert rr.patch(f"/vulnerabilities/{v['id']}", {"version": 99, "description": "x"}).status_code == 403
    # creating a vuln inside a report needs write access to that report
    assert rr.post(f"/reports/{rep['id']}/vulnerabilities", {"identifier": "pytest-x"}).status_code == 403
    assert rw.post(f"/reports/{outsider['id']}/vulnerabilities", {"identifier": "pytest-x"}).status_code == 404


def test_role_gates_and_user_management(admin, rw, rr):
    assert rr.get("/users").status_code == 403  # no directory for readers
    assert rw.get("/users").status_code == 200  # a restricted writer needs it to pick operators
    assert rw.get("/audit-logs").status_code == 403 and rr.get("/audit-logs").status_code == 403
    body = {"username": "pytest-x", "password": "Whatever-123", "role": "admin"}
    assert rw.post("/users", body).status_code == 403
    u = admin.post("/users", {"username": f"pytest-{tag()}", "password": "Temp-12345-x", "role": "read_restricted"})
    assert u.status_code == 201 and u.json()["role"] == "read_restricted"
    r = admin.patch(f"/users/{u.json()['id']}", {"role": "write_restricted"})
    assert r.json()["role"] == "write_restricted"
