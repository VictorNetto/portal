"""Report templates: who saves and sees them, and that a report gets an independent copy."""

import pytest
from conftest import make_user, new_report, tag

BODY = {
    "executive_summary_md": "## Resumo\nTexto do template.",
    "introduction_md": "Introdução padrão.",
    "sections": [
        {"title": "Metodologia", "content_markdown": "OWASP e PTES."},
        {"title": "Conclusão", "content_markdown": None},
    ],
}


@pytest.fixture(scope="module")
def rw(admin):
    return make_user(admin, "write_restricted")


def template(c, **fields):
    r = c.post("/report-templates", {"name": f"pytest-tpl-{tag()}", **BODY, **fields})
    assert r.status_code == 201, r.text
    return r.json()


def names(c):
    return {t["id"] for t in c.get("/report-templates").json()}


def test_a_report_starts_from_a_copy_of_the_template(writer):
    tpl = template(writer)
    rep = new_report(writer, template_id=tpl["id"])
    assert rep["executive_summary_md"] == BODY["executive_summary_md"]
    assert rep["introduction_md"] == BODY["introduction_md"]
    assert [(s["title"], s["content_markdown"], s["position"]) for s in rep["sections"]] == [
        ("Metodologia", "OWASP e PTES.", 1), ("Conclusão", None, 2),
    ]
    # without a template: the standard starting text, no sections
    plain = new_report(writer)
    assert plain["executive_summary_md"] and not plain["sections"] and plain["introduction_md"] is None


def test_templates_are_private_unless_an_admin_shares_them(admin, writer, writer2, rw):
    mine = template(writer)
    assert mine["mine"] and not mine["is_global"] and mine["owner"]["username"] == writer.user["username"]
    assert mine["id"] in names(writer)
    assert mine["id"] not in names(writer2) and mine["id"] not in names(rw)
    assert writer2.get(f"/report-templates/{mine['id']}").status_code == 404
    # someone else's template cannot be used to create a report
    r = writer2.post("/reports", {"name": f"pytest-{tag()}", "template_id": mine["id"]})
    assert r.status_code == 422
    # the admin sees every template...
    assert mine["id"] in names(admin)
    # ...and can make it available to everyone
    r = admin.patch(f"/report-templates/{mine['id']}", {"is_global": True})
    assert r.status_code == 200 and r.json()["is_global"]
    assert mine["id"] in names(writer2) and mine["id"] in names(rw)
    assert new_report(rw, template_id=mine["id"])["introduction_md"] == BODY["introduction_md"]


def test_readers_and_auditors_have_no_access_to_templates(admin, reader, auditor):
    shared = template(admin, is_global=True)
    for c in (reader, auditor):
        assert c.get("/report-templates").status_code == 403
        assert c.get(f"/report-templates/{shared['id']}").status_code == 403


def test_only_an_admin_shares_and_readers_cannot_save(admin, writer, reader):
    assert writer.post("/report-templates", {"name": f"pytest-tpl-{tag()}", "is_global": True}).status_code == 403
    assert template(admin, is_global=True)["is_global"]
    assert reader.post("/report-templates", {"name": f"pytest-tpl-{tag()}"}).status_code == 403
    t = template(writer)
    assert writer.patch(f"/report-templates/{t['id']}", {"is_global": True}).status_code == 403


def test_later_changes_to_the_template_do_not_reach_the_report(admin, writer):
    tpl = template(writer)
    rep = new_report(writer, template_id=tpl["id"])
    admin.patch(f"/report-templates/{tpl['id']}", {"is_global": True})
    # the report is untouched by the template change, and editing the report leaves the template alone
    writer.patch(f"/reports/{rep['id']}", {"introduction_md": "mudou no relatório"})
    assert writer.get(f"/report-templates/{tpl['id']}").json()["introduction_md"] == BODY["introduction_md"]
    assert writer.get(f"/reports/{rep['id']}").json()["introduction_md"] == "mudou no relatório"


def test_template_input_is_validated(writer):
    assert writer.post("/report-templates", {"name": "  "}).status_code == 422
    assert writer.post("/report-templates", {"name": "x" * 121}).status_code == 422
    assert writer.post("/report-templates", {"name": "ok", "sections": [{"title": ""}]}).status_code == 422
    assert writer.post("/reports", {"name": f"pytest-{tag()}", "template_id": "00000000-0000-0000-0000-000000000000"}).status_code == 422


# --- editing and deleting (option B: once shared with everyone, admins only) ---------------

def test_the_owner_edits_a_private_template(writer, writer2):
    t = template(writer)
    assert t["can_edit"] and t["version"] == 1
    r = writer.patch(f"/report-templates/{t['id']}", {
        "version": 1, "name": "  pytest-renamed  ", "introduction_md": "nova intro",
        "sections": [{"title": "Só esta", "content_markdown": "x"}, {"title": "   "}],
    })
    assert r.status_code == 200, r.text
    got = r.json()
    assert got["name"] == "pytest-renamed" and got["introduction_md"] == "nova intro" and got["version"] == 2
    assert [s["title"] for s in got["sections"]] == ["Só esta"]          # blank titles dropped
    assert got["executive_summary_md"] == BODY["executive_summary_md"]  # untouched field kept
    # someone else cannot see it, so cannot edit or delete it either
    assert writer2.patch(f"/report-templates/{t['id']}", {"version": 2, "name": "x"}).status_code == 404
    assert writer2.delete(f"/report-templates/{t['id']}").status_code == 404


def test_a_stale_edit_is_refused(writer):
    t = template(writer)
    assert writer.patch(f"/report-templates/{t['id']}", {"version": 1, "name": "pytest-a"}).status_code == 200
    r = writer.patch(f"/report-templates/{t['id']}", {"version": 1, "name": "pytest-b"})
    assert r.status_code == 409 and "Version conflict" in r.json()["detail"]
    assert writer.patch(f"/report-templates/{t['id']}", {"name": "pytest-c"}).status_code == 422   # version required


def test_once_shared_only_an_admin_changes_or_deletes_it(admin, writer, writer2):
    t = template(writer)
    admin.patch(f"/report-templates/{t['id']}", {"is_global": True})
    mine = writer.get(f"/report-templates/{t['id']}").json()
    assert mine["mine"] and not mine["can_edit"]
    r = writer.patch(f"/report-templates/{t['id']}", {"version": mine["version"], "name": "pytest-x"})
    assert r.status_code == 403 and "admin" in r.json()["detail"]
    assert writer.delete(f"/report-templates/{t['id']}").status_code == 403
    assert not writer2.get(f"/report-templates/{t['id']}").json()["can_edit"]
    # the admin can still edit it, and even unshare it (it goes back to the owner's control)
    adm = admin.get(f"/report-templates/{t['id']}").json()
    assert adm["can_edit"]
    assert admin.patch(f"/report-templates/{t['id']}", {"version": adm["version"], "name": "pytest-by-admin"}).status_code == 200
    assert admin.patch(f"/report-templates/{t['id']}", {"is_global": False}).status_code == 200
    assert writer.get(f"/report-templates/{t['id']}").json()["can_edit"]


def test_deleting_a_template_leaves_its_reports_alone(admin, writer):
    t = template(writer)
    rep = new_report(writer, template_id=t["id"])
    assert writer.delete(f"/report-templates/{t['id']}").status_code == 204
    assert writer.get(f"/report-templates/{t['id']}").status_code == 404
    assert t["id"] not in names(writer)
    kept = writer.get(f"/reports/{rep['id']}").json()
    assert kept["introduction_md"] == BODY["introduction_md"] and len(kept["sections"]) == 2
    # an admin may delete anybody's template, shared or not
    other = template(writer)
    admin.patch(f"/report-templates/{other['id']}", {"is_global": True})
    assert admin.delete(f"/report-templates/{other['id']}").status_code == 204
    entries = admin.get("/audit-logs", params={"entity_type": "report_template", "action": "delete"}).json()
    rows = entries["items"] if isinstance(entries, dict) else entries
    assert any(str(e.get("entity_id")) == other["id"] for e in rows)


def test_only_admins_share_or_unshare(writer):
    t = template(writer)
    assert writer.patch(f"/report-templates/{t['id']}", {"is_global": True}).status_code == 403
