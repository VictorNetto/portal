"""The audit page's filters (POST /audit-logs/search): the Hub's grammar, applied in SQL."""

from datetime import UTC, datetime, timedelta

from conftest import make_user, new_vuln, png_bytes, saved_vuln, tag, upload


def search(c, *filters, page_size=200):
    r = c.post("/audit-logs/search", {"filters": list(filters), "page_size": page_size})
    assert r.status_code == 200, r.text
    return r.json()


def test_filters_by_actor_action_record_and_date(admin):
    me = make_user(admin, "write_all")
    nick = f"Auditada {tag()}"
    me.patch("/auth/me", {"full_name": None, "display_name": nick})
    v = new_vuln(me)
    me.patch(f"/vulnerabilities/{v['id']}", {"version": v["version"], "description": "changed"})

    # actor: by login or by name; the entry names the person
    mine = search(admin, {"key": "actor", "text": me.user["username"]})
    assert mine["total"] >= 3 and all(e["actor"] == me.user["username"] for e in mine["items"])
    assert mine["items"][0]["actor_name"] == nick
    assert search(admin, {"key": "actor", "text": nick.split()[1]})["total"] == mine["total"]

    # action (any of) and its negation
    upd = search(admin, {"key": "actor", "text": me.user["username"]}, {"key": "action", "values": ["update"]})
    assert upd["total"] >= 2 and {e["action"] for e in upd["items"]} == {"update"}
    rest = search(admin, {"key": "actor", "text": me.user["username"]},
                  {"key": "action", "values": ["update"], "negate": True})
    assert rest["total"] == mine["total"] - upd["total"]

    # record: the internal id once sent… here a uuid, and the entry carries a label
    rec = search(admin, {"key": "record", "text": v["id"]})
    assert rec["total"] >= 2 and all(e["entity_id"] == v["id"] for e in rec["items"])
    assert rec["items"][0]["entity_label"] == (v["internal_id"] or v["identifier"])

    # date: a window that ends before now has none of it
    past = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    assert search(admin, {"key": "actor", "text": me.user["username"]}, {"key": "date", "to": past})["total"] == 0
    assert search(admin, {"key": "actor", "text": me.user["username"]}, {"key": "date", "from": past})["total"] == mine["total"]

    # role and entity
    assert search(admin, {"key": "actor", "text": me.user["username"]},
                  {"key": "role", "values": ["read_all"]})["total"] == 0
    ent = search(admin, {"key": "actor", "text": me.user["username"]}, {"key": "entity", "values": ["vulnerability"]})
    assert ent["total"] >= 2 and {e["entity_type"] for e in ent["items"]} == {"vulnerability"}


def test_record_by_internal_id_includes_attachments_and_free_text(admin, writer):
    r = saved_vuln(writer)                    # a completed vuln has its VULN-… id
    assert r["internal_id"]
    v = new_vuln(writer)
    assert upload(writer, f"/vulnerabilities/{v['id']}/attachments", "shot.png", png_bytes()).status_code == 201
    got = search(admin, {"key": "record", "text": r["internal_id"].lower()})
    assert got["total"] >= 1 and all(e["entity_id"] == r["id"] for e in got["items"])
    att = search(admin, {"key": "record", "text": v["id"]}, {"key": "entity", "values": ["attachment"]})
    assert att["total"] == 1 and att["items"][0]["entity_label"] == "shot.png"

    # free text finds the record by its internal id, the detail or the actor
    assert any(e["entity_id"] == r["id"] for e in search(admin, {"key": "text", "text": r["internal_id"]})["items"])
    marker = f"Marca {tag()}"
    writer.patch("/auth/me", {"full_name": None, "display_name": marker})
    hits = search(admin, {"key": "detail", "text": marker.lower()})["items"]
    assert [e["entity_id"] for e in hits] == [writer.user["id"]]
    # free text also matches the actor by name: everything that writer did
    hits = search(admin, {"key": "text", "text": marker.lower()})["items"]
    assert len(hits) > 1 and all(e["actor"] == writer.user["username"] for e in hits)


def test_failed_logins_system_ip_and_validation(admin, auditor, writer):
    name = f"pytest-ghost-{tag()}"
    from conftest import login
    login(name, "wrong-password-1")
    hit = search(admin, {"key": "actor", "text": name})
    assert hit["total"] == 1 and hit["items"][0]["action"] == "login_failed"
    assert search(admin, {"key": "ip", "text": hit["items"][0]["ip_address"] or "."})["total"] >= 1

    # an auditor may search; a writer may not
    assert auditor.post("/audit-logs/search", {"filters": []}).status_code == 200
    assert writer.post("/audit-logs/search", {"filters": []}).status_code == 403

    # bad tokens are refused
    for bad in ({"key": "action", "values": ["nope"]}, {"key": "date"}, {"key": "actor", "text": " "},
                {"key": "role", "values": []}, {"key": "whatever", "text": "x"}):
        assert admin.post("/audit-logs/search", {"filters": [bad]}).status_code == 422, bad

    facets = admin.get("/audit-logs/facets").json()
    assert "system" in facets["actors"] and "vulnerability" in facets["entity_types"] and "none" in facets["entity_types"]
    assert writer.get("/audit-logs/facets").status_code == 403
