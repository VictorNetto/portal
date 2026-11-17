"""A user's full name and display name: set on Perfil, shown to others instead of the login."""

import io

from conftest import make_user, new_report, new_vuln
from docx import Document


def test_a_user_sets_their_own_names(admin):
    me = make_user(admin, "write_all")
    r = me.patch("/auth/me", {"full_name": "  Maria   da Silva ", "display_name": "Maria"})
    assert r.status_code == 200, r.text
    assert r.json()["full_name"] == "Maria da Silva" and r.json()["display_name"] == "Maria"
    assert r.json()["username"] == me.user["username"]           # the login does not change
    assert me.get("/auth/me").json()["display_name"] == "Maria"

    # Blank clears; too long is refused.
    r = me.patch("/auth/me", {"full_name": "Maria da Silva", "display_name": "  "})
    assert r.json()["display_name"] is None
    assert me.patch("/auth/me", {"full_name": "x" * 151, "display_name": None}).status_code == 422

    # The change is audited.
    r = admin.get("/audit-logs", params={"entity_type": "user", "page_size": 200})
    assert r.status_code == 200, r.text
    assert any(e["entity_id"] == me.user["id"] and (e["detail"] or {}).get("display_name")
               for e in r.json()["items"])


def test_others_see_the_display_name_and_documents_the_full_name(admin, writer):
    op = make_user(admin, "write_all")
    op.patch("/auth/me", {"full_name": "Joao Pereira Santos", "display_name": "Joao P."})
    v = new_vuln(writer, operator_ids=[op.user["id"]])
    got = writer.get(f"/vulnerabilities/{v['id']}").json()
    assert got["operators"] == [{"id": op.user["id"], "username": op.user["username"], "name": "Joao P."}]

    users = {u["id"]: u for u in writer.get("/users").json()}
    assert users[op.user["id"]]["display_name"] == "Joao P."

    body = "\n".join(p.text for p in Document(io.BytesIO(
        writer.get(f"/vulnerabilities/{v['id']}/export", params={"format": "docx"}).content)).paragraphs)
    doc_tables = Document(io.BytesIO(
        writer.get(f"/vulnerabilities/{v['id']}/export", params={"format": "docx"}).content)).tables
    cells = "\n".join(c.text for t in doc_tables for row in t.rows for c in row.cells)
    assert "Joao Pereira Santos" in body + cells and op.user["username"] not in body + cells

    # Without names, the login is what shows.
    plain = make_user(admin, "write_all")
    rid = new_report(writer, operator_ids=[plain.user["id"]])["id"]
    assert writer.get(f"/reports/{rid}").json()["operators"][0]["name"] == plain.user["username"]


def test_the_lock_names_its_holder(admin):
    me = make_user(admin, "write_all")
    me.patch("/auth/me", {"full_name": None, "display_name": "Ana"})
    rid = new_report(me)["id"]
    lock = me.post(f"/reports/{rid}/lock").json()["lock"]
    assert lock["holder_name"] == "Ana" and lock["holder_username"] == me.user["username"]


def test_an_admin_may_set_a_users_names(admin, writer):
    u = make_user(admin, "read_all")
    r = admin.patch(f"/users/{u.user['id']}", {"full_name": "Carla Souza"})
    assert r.status_code == 200 and r.json()["full_name"] == "Carla Souza"
    # A field not sent is left alone.
    admin.patch(f"/users/{u.user['id']}", {"display_name": "Carla"})
    got = admin.get(f"/users/{u.user['id']}").json()
    assert got["full_name"] == "Carla Souza" and got["display_name"] == "Carla"
    # Only admins.
    assert writer.patch(f"/users/{u.user['id']}", {"full_name": "X"}).status_code == 403
