"""The defense-team role (D17): sees sent vulns only, accepts them, records the RVS ID."""

import pytest

from tests.conftest import (
    make_user,
    new_report,
    new_vuln,
    png_bytes,
    report_vuln,
    saved_vuln,
    tag,
    upload,
)


@pytest.fixture(scope="module")
def defense(admin):
    return make_user(admin, "defense")


def sent_vuln(c, **fields) -> dict:
    v = saved_vuln(c, **fields)
    r = c.post(f"/vulnerabilities/{v['id']}/send")
    assert r.status_code == 200, r.text
    return r.json()


def test_sees_only_sent_vulns(writer, defense):
    draft, ready, sent = new_vuln(writer), saved_vuln(writer), sent_vuln(writer)
    ids = {v["id"] for v in defense.get("/defense/vulnerabilities").json()}
    assert sent["id"] in ids
    assert draft["id"] not in ids and ready["id"] not in ids
    for v in (draft, ready):
        assert defense.get(f"/defense/vulnerabilities/{v['id']}").status_code == 404


def test_vulns_of_a_draft_report_stay_hidden(writer, defense):
    rep = new_report(writer)
    v = report_vuln(writer, rep["id"])
    assert defense.get(f"/defense/vulnerabilities/{v['id']}").status_code == 404


def test_detail_leaves_out_red_team_internals(writer, defense):
    v = sent_vuln(writer, internal_notes="só para o red team")
    body = defense.get(f"/defense/vulnerabilities/{v['id']}").json()
    assert body["identifier"] == v["identifier"] and body["mitigation"] == "m"
    for hidden in ("internal_notes", "operators", "viewers", "created_by", "version"):
        assert hidden not in body


def test_reaches_nothing_of_the_red_team(writer, defense):
    v = sent_vuln(writer)
    for path in ("/vulnerabilities", f"/vulnerabilities/{v['id']}", "/reports", "/rvs-queue",
                 "/report-templates", "/users", f"/vulnerabilities/{v['id']}/attachments"):
        assert defense.get(path).status_code == 403, path
    assert defense.post(f"/vulnerabilities/{v['id']}/rvs", {"rvs_id": "X"}).status_code == 403
    assert defense.post("/vulnerabilities", {"identifier": "pytest-x"}).status_code == 403
    assert defense.get("/auth/me").status_code == 200


def test_red_team_cannot_use_defense_routes(writer):
    assert writer.get("/defense/vulnerabilities").status_code == 403


def test_accept_then_rvs(writer, defense):
    v = sent_vuln(writer)
    path = f"/defense/vulnerabilities/{v['id']}"
    r = defense.post(f"{path}/rvs", {"rvs_id": "RVS-early"})
    assert r.status_code == 409  # accept first

    r = defense.post(f"{path}/accept")
    assert r.status_code == 200, r.text
    assert r.json()["accepted_at"] and r.json()["accepter"]["username"] == defense.user["username"]
    assert defense.post(f"{path}/accept").status_code == 409

    rvs = f"RVS-pytest-{tag()}"
    r = defense.post(f"{path}/rvs", {"rvs_id": rvs})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "fixing" and r.json()["rvs_id"] == rvs
    assert defense.post(f"{path}/rvs", {"rvs_id": "again"}).status_code == 409

    # The red team sees who accepted it, and the vuln left their RVS queue.
    mine = writer.get(f"/vulnerabilities/{v['id']}").json()
    assert mine["accepted_at"] and mine["accepter"]["username"] == defense.user["username"]
    assert v["id"] not in {x["id"] for x in writer.get("/rvs-queue").json()}
    # Still on the defense list as it moves on.
    assert defense.get(path).json()["status"] == "fixing"


def test_accept_and_rvs_are_audited(admin, writer, defense):
    v = sent_vuln(writer)
    defense.post(f"/defense/vulnerabilities/{v['id']}/accept")
    defense.post(f"/defense/vulnerabilities/{v['id']}/rvs", {"rvs_id": f"RVS-{tag()}"})
    rows = admin.get("/audit-logs", params={"entity_type": "vulnerability", "page_size": 200}).json()["items"]
    mine = [r for r in rows if r["entity_id"] == v["id"] and r["actor"] == defense.user["username"]]
    assert {r["action"] for r in mine} >= {"accept", "status_change"}


def test_attachments_of_a_sent_vuln(writer, defense):
    v = saved_vuln(writer)
    att = upload(writer, f"/vulnerabilities/{v['id']}/attachments", "e.png", png_bytes()).json()
    assert defense.get(f"/defense/attachments/{att['id']}/content").status_code == 404  # not sent yet
    writer.post(f"/vulnerabilities/{v['id']}/send")
    listed = defense.get(f"/defense/vulnerabilities/{v['id']}/attachments").json()
    assert [a["id"] for a in listed] == [att["id"]]
    r = defense.get(f"/defense/attachments/{att['id']}/content")
    assert r.status_code == 200 and r.content == png_bytes()


def test_cannot_be_operator_or_viewer(writer, defense):
    r = writer.post("/vulnerabilities", {"identifier": f"pytest-{tag()}", "operator_ids": [defense.user["id"]]})
    assert r.status_code == 422
    r = writer.post("/vulnerabilities", {"identifier": f"pytest-{tag()}", "viewer_ids": [defense.user["id"]]})
    assert r.status_code == 422


def test_correction_before_sent_clears_acceptance(admin, writer, defense):
    v = sent_vuln(writer)
    defense.post(f"/defense/vulnerabilities/{v['id']}/accept")
    r = admin.post(f"/vulnerabilities/{v['id']}/correction", {"to": "ready", "reason": "sent too early"})
    assert r.status_code == 200, r.text
    assert r.json()["accepted_at"] is None
    assert defense.get(f"/defense/vulnerabilities/{v['id']}").status_code == 404


def test_admin_sees_defense_scope(admin, defense):
    assert admin.get(f"/users/{defense.user['id']}/access").json()["scope"] == "sent"
