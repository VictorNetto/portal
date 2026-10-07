"""Reports: write lock, sections, vulnerabilities inside a report, deletion."""

from datetime import timedelta

from sqlalchemy import text

from app.db import SessionLocal
from conftest import new_report, report_vuln, tag


def test_creating_a_report_gives_an_id_a_template_and_the_lock(writer):
    r = new_report(writer, client_name="ACME", start_date="2026-10-01", end_date="2026-10-05")
    assert r["status"] == "draft" and r["internal_id"].startswith("OP-")
    assert "Objetivo" in r["executive_summary_md"]
    assert r["lock"]["mine"] and r["lock"]["holder_username"] == writer.user["username"]


def test_report_input_is_validated(writer):
    assert writer.post("/reports", {"name": ""}).status_code == 422
    assert writer.post("/reports", {"name": "pytest-x", "start_date": "2026-10-05", "end_date": "2026-10-01"}).status_code == 422
    r = new_report(writer)
    assert writer.patch(f"/reports/{r['id']}", {"name": "   "}).status_code == 422
    assert writer.patch(f"/reports/{r['id']}", {"start_date": "2026-10-05", "end_date": "2026-10-01"}).status_code == 422


def test_only_the_lock_holder_can_edit(writer, writer2, reader):
    r = new_report(writer)
    rid = r["id"]
    assert writer.patch(f"/reports/{rid}", {"scope": "mine"}).status_code == 200
    other = writer2.get(f"/reports/{rid}").json()
    assert other["lock"]["holder_username"] == writer.user["username"] and not other["lock"]["mine"]
    assert writer2.patch(f"/reports/{rid}", {"scope": "theirs"}).status_code == 409
    assert writer2.post(f"/reports/{rid}/lock").status_code == 409           # cannot take a held lock
    assert reader.post(f"/reports/{rid}/lock").status_code == 403
    assert reader.patch(f"/reports/{rid}", {"scope": "x"}).status_code == 403


def test_lock_handover_heartbeat_and_release(writer, writer2):
    rid = new_report(writer)["id"]
    assert writer.post(f"/reports/{rid}/lock/heartbeat").status_code == 200
    assert writer2.post(f"/reports/{rid}/lock/heartbeat").status_code == 409
    assert writer.delete(f"/reports/{rid}/lock").status_code == 204
    assert writer2.post(f"/reports/{rid}/lock").json()["lock"]["mine"]
    assert writer.patch(f"/reports/{rid}", {"scope": "x"}).status_code == 409   # the first holder lost it


def test_admin_can_force_release_and_it_is_audited(admin, writer, writer2):
    rid = new_report(writer)["id"]
    assert writer2.post(f"/reports/{rid}/lock/force-release").status_code == 403    # not a writer's power
    assert admin.post(f"/reports/{rid}/lock/force-release").status_code == 204
    assert writer.patch(f"/reports/{rid}", {"scope": "x"}).status_code == 409
    items = admin.get("/audit-logs", params={"action": "lock_override", "page_size": 200}).json()["items"]
    mine = [e for e in items if e["entity_id"] == rid]
    assert mine and mine[0]["detail"]["previous_holder"] == writer.user["username"]


def test_an_idle_lock_frees_itself_after_ten_minutes(writer, writer2):
    rid = new_report(writer)["id"]
    with SessionLocal() as s:
        s.execute(text("UPDATE reports SET lock_last_activity_at = now() - interval '11 minutes' WHERE id = :i"), {"i": rid})
        s.commit()
    assert writer2.get(f"/reports/{rid}").json()["lock"] is None                  # shown as free
    taken = writer2.post(f"/reports/{rid}/lock")
    assert taken.status_code == 200 and taken.json()["lock"]["holder_username"] == writer2.user["username"]


def test_sections_add_rename_reorder_remove(writer):
    rid = new_report(writer)["id"]
    for title in ("Metodologia", "Escopo", "Anexos"):
        r = writer.post(f"/reports/{rid}/sections", {"title": title, "content_markdown": f"# {title}"})
    sections = r.json()["sections"]
    assert [s["title"] for s in sections] == ["Metodologia", "Escopo", "Anexos"]
    assert [s["position"] for s in sections] == [1, 2, 3]
    ids = [s["id"] for s in sections]

    r = writer.post(f"/reports/{rid}/sections/reorder", {"ids": [ids[2], ids[0], ids[1]]})
    assert [s["title"] for s in r.json()["sections"]] == ["Anexos", "Metodologia", "Escopo"]
    assert writer.post(f"/reports/{rid}/sections/reorder", {"ids": ids[:2]}).status_code == 422   # must list them all

    r = writer.patch(f"/reports/{rid}/sections/{ids[0]}", {"title": "Metodologia v2"})
    assert any(s["title"] == "Metodologia v2" for s in r.json()["sections"])
    assert writer.patch(f"/reports/{rid}/sections/{ids[0]}", {"title": " "}).status_code == 422

    r = writer.delete(f"/reports/{rid}/sections/{ids[2]}")
    assert [s["position"] for s in r.json()["sections"]] == [1, 2]                # the gap closes


def test_vulns_inside_a_report_are_not_standalone(writer, writer2):
    rid = new_report(writer)["id"]
    low = report_vuln(writer, rid, cvss_score=3.1)
    high = report_vuln(writer, rid, cvss_score=9.1)
    none = report_vuln(writer, rid)
    assert high["report_id"] == rid and high["status"] == "draft" and high["internal_id"] is None

    rep = writer.get(f"/reports/{rid}").json()
    assert [v["id"] for v in rep["vulnerabilities"]] == [high["id"], low["id"], none["id"]]   # CVSS descending
    assert rep["vuln_count"] == 3 and float(rep["max_cvss"]) == 9.1

    assert high["id"] not in [v["id"] for v in writer.get("/vulnerabilities").json()]        # not in the normal list
    assert writer2.get(f"/vulnerabilities/{high['id']}").status_code == 200                   # but anyone can read it
    assert writer.post(f"/vulnerabilities/{high['id']}/send").status_code == 404              # no life of its own
    assert writer.post(f"/vulnerabilities/{high['id']}/dispatch").status_code == 404


def test_editing_a_report_vuln_needs_the_report_lock(writer, writer2):
    rid = new_report(writer)["id"]
    v = report_vuln(writer, rid)
    assert writer2.patch(f"/vulnerabilities/{v['id']}", {"version": v["version"], "description": "x"}).status_code == 409
    ok = writer.patch(f"/vulnerabilities/{v['id']}", {"version": v["version"], "description": "updated"})
    assert ok.status_code == 200 and ok.json()["description"] == "updated"
    assert writer2.delete(f"/vulnerabilities/{v['id']}").status_code == 409


def test_deleting_a_draft_report_takes_its_vulns_with_it(writer, writer2):
    rid = new_report(writer)["id"]
    v = report_vuln(writer, rid)
    assert writer2.delete(f"/reports/{rid}").status_code == 409            # held by another operator
    assert writer.delete(f"/reports/{rid}").status_code == 204
    assert writer.get(f"/reports/{rid}").status_code == 404
    assert writer.get(f"/vulnerabilities/{v['id']}").status_code == 404
    assert rid not in [r["id"] for r in writer.get("/reports").json()]


def test_report_reads_are_audited(admin, writer):
    rid = new_report(writer)["id"]
    writer.get(f"/reports/{rid}")
    items = admin.get("/audit-logs", params={"action": "read", "page_size": 200}).json()["items"]
    assert any(e["entity_id"] == rid and e["actor"] == writer.user["username"] for e in items)


def test_list_item_summarises_the_report(writer):
    rid = new_report(writer, client_name="Globex")["id"]
    report_vuln(writer, rid, cvss_score=6.5)
    row = next(r for r in writer.get("/reports").json() if r["id"] == rid)
    assert row["client_name"] == "Globex" and row["vuln_count"] == 1 and float(row["max_cvss"]) == 6.5
    assert row["lock"]["holder_username"] == writer.user["username"]
