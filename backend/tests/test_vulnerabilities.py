"""Vulnerability lifecycle, field locks, concurrency, corrections."""

from concurrent.futures import ThreadPoolExecutor

import httpx
from conftest import BASE_URL, fixing_vuln, new_vuln, saved_vuln, tag


def test_send_requires_the_mandatory_fields(writer):
    v = writer.post("/vulnerabilities", {"identifier": f"pytest-{tag()}"}).json()
    r = writer.post(f"/vulnerabilities/{v['id']}/complete")
    assert r.status_code == 422
    for field in ("description", "finding_detail", "mitigation"):
        assert field in r.json()["detail"]


def test_a_draft_can_be_saved_incomplete(writer):
    r = writer.post("/vulnerabilities", {"description": "only a description"})
    assert r.status_code == 201 and r.json()["status"] == "draft" and r.json()["identifier"] is None


def test_send_assigns_an_internal_id_and_timestamp(writer):
    v = saved_vuln(writer)
    assert v["status"] == "ready"
    assert v["internal_id"].startswith("VULN-")
    assert v["ready_at"]


def test_send_then_rvs_starts_the_fix(writer):
    v = saved_vuln(writer)
    d = writer.post(f"/vulnerabilities/{v['id']}/send").json()
    assert d["status"] == "sent" and d["sent_at"]
    queue = [x["id"] for x in writer.get("/rvs-queue").json()]
    assert v["id"] in queue
    a = writer.post(f"/vulnerabilities/{v['id']}/rvs", {"rvs_id": "RVS-pytest-1"}).json()
    assert a["status"] == "fixing" and a["rvs_id"] == "RVS-pytest-1" and a["fixing_at"]
    assert v["id"] not in [x["id"] for x in writer.get("/rvs-queue").json()]


def test_rvs_id_can_be_set_only_once_and_only_when_sent_vuln(writer):
    v = saved_vuln(writer)
    assert writer.post(f"/vulnerabilities/{v['id']}/rvs", {"rvs_id": "x"}).status_code == 409  # not sent yet
    writer.post(f"/vulnerabilities/{v['id']}/send")
    assert writer.post(f"/vulnerabilities/{v['id']}/rvs", {"rvs_id": "  "}).status_code == 422
    assert writer.post(f"/vulnerabilities/{v['id']}/rvs", {"rvs_id": "RVS-A"}).status_code == 200
    assert writer.post(f"/vulnerabilities/{v['id']}/rvs", {"rvs_id": "RVS-B"}).status_code == 409


def test_cannot_skip_steps(writer):
    d = new_vuln(writer)
    assert writer.post(f"/vulnerabilities/{d['id']}/send").status_code == 409  # draft
    s = saved_vuln(writer)
    assert writer.post(f"/vulnerabilities/{s['id']}/complete").status_code == 409      # already sent


def test_retest_loop_to_fixed(writer):
    v = fixing_vuln(writer)
    move = lambda to: writer.post(f"/vulnerabilities/{v['id']}/transition", {"to": to})
    assert move("fixed").status_code == 409              # cannot jump
    assert move("fixed").status_code == 409                # must go through retesting
    assert v["fixing_at"]
    r = move("retesting").json(); assert r["retesting_at"]
    r = move("fixing").json()                        # retest failed
    assert r["status"] == "fixing" and r["retesting_at"] is None
    move("retesting")
    r = move("fixed").json()
    assert r["status"] == "fixed" and r["fixed_at"]
    assert move("fixing").status_code == 409         # terminal for normal users


def test_two_simultaneous_transitions_only_one_wins(writer):
    v = fixing_vuln(writer)

    def go():
        return httpx.post(f"{BASE_URL}/vulnerabilities/{v['id']}/transition", json={"to": "retesting"},
                          headers={"Authorization": f"Bearer {writer.token}"}, timeout=60).status_code

    with ThreadPoolExecutor(2) as pool:
        codes = sorted(f.result() for f in [pool.submit(go), pool.submit(go)])
    assert codes == [200, 409]


def test_admin_correction(admin, writer):
    v = fixing_vuln(writer)
    writer.post(f"/vulnerabilities/{v['id']}/transition", {"to": "retesting"})
    body = {"to": "sent", "reason": "Wrong RVS id entered"}
    assert writer.post(f"/vulnerabilities/{v['id']}/correction", body).status_code == 403   # admin only
    assert admin.post(f"/vulnerabilities/{v['id']}/correction", {**body, "reason": "abc"}).status_code == 422
    assert admin.post(f"/vulnerabilities/{v['id']}/correction", {"to": "fixed", "reason": "forward is not a correction"}).status_code == 409
    assert admin.post(f"/vulnerabilities/{v['id']}/correction", {"to": "draft", "reason": "back to draft?"}).status_code == 422

    r = admin.post(f"/vulnerabilities/{v['id']}/correction", body).json()
    assert r["status"] == "sent" and r["rvs_id"] is None
    assert r["fixing_at"] is None and r["retesting_at"] is None
    assert v["id"] in [x["id"] for x in admin.get("/rvs-queue").json()]        # back in the queue
    assert admin.post(f"/vulnerabilities/{v['id']}/rvs", {"rvs_id": "RVS-right"}).status_code == 200

    log = admin.get("/audit-logs", params={"action": "correction", "page_size": 200}).json()["items"]
    mine = [e for e in log if e["entity_id"] == v["id"]]
    assert mine and all(e["detail"].get("reason") for e in mine)
    assert any(e["detail"].get("rvs_id_removed") for e in mine)


def test_fields_lock_as_the_vuln_progresses(writer):
    v = saved_vuln(writer)
    ok = writer.patch(f"/vulnerabilities/{v['id']}", {"version": v["version"], "description": "edited"})
    assert ok.status_code == 200                                                  # ready: everything editable
    v = ok.json()
    d = writer.post(f"/vulnerabilities/{v['id']}/send").json()
    locked = writer.patch(f"/vulnerabilities/{v['id']}", {"version": d["version"], "description": "nope"})
    assert locked.status_code == 422 and "description" in locked.json()["detail"]
    notes = writer.patch(f"/vulnerabilities/{v['id']}", {"version": d["version"], "internal_notes": "still allowed"})
    assert notes.status_code == 200


def test_stale_version_is_rejected(writer):
    v = new_vuln(writer)
    assert writer.patch(f"/vulnerabilities/{v['id']}", {"version": v["version"], "cwe": "CWE-79"}).status_code == 200
    stale = writer.patch(f"/vulnerabilities/{v['id']}", {"version": v["version"], "cwe": "CWE-89"})
    assert stale.status_code == 409


def test_cvss_range_is_validated(writer):
    assert writer.post("/vulnerabilities", {"identifier": "pytest-x", "cvss_score": 11}).status_code == 422
    assert writer.post("/vulnerabilities", {"identifier": "pytest-x", "cvss_score": -1}).status_code == 422


def test_operators_can_be_assigned_and_replaced(admin, writer, writer2):
    v = new_vuln(writer, operator_ids=[writer.user["id"]])
    assert [o["id"] for o in v["operators"]] == [writer.user["id"]]
    r = writer.patch(f"/vulnerabilities/{v['id']}", {"version": v["version"], "operator_ids": [writer2.user["id"]]}).json()
    assert [o["id"] for o in r["operators"]] == [writer2.user["id"]]
    unknown = writer.post("/vulnerabilities", {"identifier": "pytest-x", "operator_ids": ["00000000-0000-0000-0000-000000000000"]})
    assert unknown.status_code == 422


def test_delete_is_soft_and_hides_the_record(writer):
    v = new_vuln(writer)
    assert writer.delete(f"/vulnerabilities/{v['id']}").status_code == 204
    assert writer.get(f"/vulnerabilities/{v['id']}").status_code == 404
    assert v["id"] not in [x["id"] for x in writer.get("/vulnerabilities").json()]


def test_readers_see_everything_but_change_nothing(reader, writer):
    v = saved_vuln(writer)
    assert reader.get(f"/vulnerabilities/{v['id']}").status_code == 200
    assert reader.patch(f"/vulnerabilities/{v['id']}", {"version": v["version"], "cwe": "CWE-1"}).status_code == 403
    assert reader.post(f"/vulnerabilities/{v['id']}/send").status_code == 403
    assert reader.delete(f"/vulnerabilities/{v['id']}").status_code == 403


def test_list_exposes_what_the_hub_needs(writer):
    v = saved_vuln(writer, source="nuclei", cvss_score=7.5, cvss_vector="AV:N/AC:L")
    row = next(x for x in writer.get("/vulnerabilities").json() if x["id"] == v["id"])
    for key in ("source", "cvss_vector", "rvs_id", "created_at", "updated_at", "ready_at", "operators"):
        assert key in row
    assert row["source"] == "nuclei" and row["ready_at"]


def test_transitions_are_audited_with_the_actor(admin, writer):
    v = saved_vuln(writer)
    items = admin.get("/audit-logs", params={"action": "status_change", "page_size": 200}).json()["items"]
    mine = [e for e in items if e["entity_id"] == v["id"]]
    assert mine and mine[0]["actor"] == writer.user["username"] and mine[0]["detail"]["to"] == "ready"
