"""Report templates: who saves, sees, edits and shares them (sharing is reviewed by an admin),
and that a report gets an independent copy."""

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


def sharing(c, tpl, action):
    return c.post(f"/report-templates/{tpl['id']}/sharing", {"action": action})


def shared(owner, admin, **fields):
    """A template its owner asked to share and an admin approved."""
    t = template(owner, **fields)
    assert sharing(owner, t, "request").status_code == 200
    r = sharing(admin, t, "approve")
    assert r.status_code == 200, r.text
    return r.json()


def ids(c):
    return {t["id"] for t in c.get("/report-templates").json()}


# --- copies -------------------------------------------------------------------------------

def test_a_report_starts_from_a_copy_of_the_template(writer):
    tpl = template(writer)
    rep = new_report(writer, template_id=tpl["id"])
    assert rep["executive_summary_md"] == BODY["executive_summary_md"]
    assert rep["introduction_md"] == BODY["introduction_md"]
    assert [(s["title"], s["content_markdown"], s["position"]) for s in rep["sections"]] == [
        ("Metodologia", "OWASP e PTES.", 1), ("Conclusão", None, 2),
    ]
    plain = new_report(writer)  # without a template: the standard starting text, no sections
    assert plain["executive_summary_md"] and not plain["sections"] and plain["introduction_md"] is None


def test_editing_never_reaches_reports_already_created(writer):
    tpl = template(writer)
    rep = new_report(writer, template_id=tpl["id"])
    assert writer.patch(f"/report-templates/{tpl['id']}", {"version": 1, "introduction_md": "mudou"}).status_code == 200
    assert writer.get(f"/reports/{rep['id']}").json()["introduction_md"] == BODY["introduction_md"]


# --- private templates ------------------------------------------------------------------------

def test_a_new_template_is_private_and_its_owner_edits_it(writer, writer2, rw):
    t = template(writer)
    assert t["share_status"] == "private" and t["mine"] and t["can_edit"] and t["actions"] == ["request"]
    assert t["id"] in ids(writer) and t["id"] not in ids(writer2) and t["id"] not in ids(rw)
    assert writer2.get(f"/report-templates/{t['id']}").status_code == 404
    assert writer2.post("/reports", {"name": f"pytest-{tag()}", "template_id": t["id"]}).status_code == 422
    r = writer.patch(f"/report-templates/{t['id']}", {
        "version": 1, "name": "  pytest-renamed  ",
        "sections": [{"title": "Só esta", "content_markdown": "x"}, {"title": "   "}],
    })
    assert r.status_code == 200, r.text
    got = r.json()
    assert got["name"] == "pytest-renamed" and got["version"] == 2
    assert [s["title"] for s in got["sections"]] == ["Só esta"]
    assert got["introduction_md"] == BODY["introduction_md"]
    assert writer2.patch(f"/report-templates/{t['id']}", {"version": 2, "name": "x"}).status_code == 404


def test_a_stale_edit_is_refused(writer):
    t = template(writer)
    assert writer.patch(f"/report-templates/{t['id']}", {"version": 1, "name": "pytest-a"}).status_code == 200
    r = writer.patch(f"/report-templates/{t['id']}", {"version": 1, "name": "pytest-b"})
    assert r.status_code == 409 and "Version conflict" in r.json()["detail"]


# --- the sharing review ------------------------------------------------------------------------

def test_sharing_needs_the_owners_request_and_an_admins_approval(admin, writer, writer2):
    t = template(writer)
    # nobody shares directly: not at creation, not by an admin on someone else's private template
    assert admin.post("/report-templates", {"name": f"pytest-{tag()}", "is_global": True}).json()["share_status"] == "private"
    assert sharing(admin, t, "approve").status_code == 409       # nothing was requested
    assert sharing(admin, t, "request").status_code == 403       # only the owner asks
    assert sharing(writer2, t, "request").status_code == 404     # cannot even see it

    r = sharing(writer, t, "request")
    assert r.status_code == 200
    pending = r.json()
    assert pending["share_status"] == "pending" and pending["share_requested_at"] and pending["actions"] == ["withdraw"]
    assert not pending["can_edit"]                                # frozen while it waits
    assert writer.patch(f"/report-templates/{t['id']}", {"version": pending["version"], "name": "x"}).status_code == 403
    assert t["id"] not in ids(writer2)                             # still not shared
    assert sharing(writer, t, "approve").status_code == 403       # the owner cannot approve

    adm = admin.get(f"/report-templates/{t['id']}").json()
    assert set(adm["actions"]) == {"approve", "reject"}
    r = sharing(admin, t, "approve")
    assert r.status_code == 200
    got = r.json()
    assert got["share_status"] == "shared" and got["is_global"] and got["share_decided_by"]["username"] == "admin"
    assert t["id"] in ids(writer2)
    assert new_report(writer2, template_id=t["id"])["introduction_md"] == BODY["introduction_md"]


def test_the_owner_can_withdraw_a_request_and_an_admin_can_reject_one(admin, writer, writer2):
    t = template(writer)
    sharing(writer, t, "request")
    assert sharing(writer, t, "withdraw").json()["share_status"] == "private"
    assert writer.get(f"/report-templates/{t['id']}").json()["can_edit"]
    sharing(writer, t, "request")
    r = sharing(admin, t, "reject")
    assert r.status_code == 200 and r.json()["share_status"] == "private"
    assert t["id"] not in ids(writer2)
    assert writer.get(f"/report-templates/{t['id']}").json()["can_edit"]   # back in the owner's hands


def test_once_shared_the_owner_can_no_longer_change_or_delete_it(admin, writer):
    t = shared(writer, admin)
    mine = writer.get(f"/report-templates/{t['id']}").json()
    assert mine["mine"] and not mine["can_edit"] and mine["actions"] == []
    r = writer.patch(f"/report-templates/{t['id']}", {"version": mine["version"], "name": "pytest-x"})
    assert r.status_code == 403 and "new template" in r.json()["detail"]
    assert writer.delete(f"/report-templates/{t['id']}").status_code == 403
    assert sharing(writer, t, "withdraw").status_code == 409
    # an admin still can
    adm = admin.get(f"/report-templates/{t['id']}").json()
    assert adm["can_edit"] and admin.patch(
        f"/report-templates/{t['id']}", {"version": adm["version"], "name": "pytest-by-admin"}).status_code == 200


def test_an_unshared_template_is_available_to_nobody_until_shared_again(admin, writer, writer2):
    t = shared(writer, admin)
    assert sharing(writer, t, "unshare").status_code == 403      # admins only
    r = sharing(admin, t, "unshare")
    assert r.status_code == 200 and r.json()["share_status"] == "unshared"
    for c in (writer, writer2):                                  # its owner included
        assert t["id"] not in ids(c)
        assert c.get(f"/report-templates/{t['id']}").status_code == 404
        assert c.post("/reports", {"name": f"pytest-{tag()}", "template_id": t["id"]}).status_code == 422
    # admins still see it (to share it again or delete it), but nobody can start a report from it
    adm = admin.get(f"/report-templates/{t['id']}").json()
    assert not adm["can_use"] and adm["actions"] == ["reshare"]
    assert admin.post("/reports", {"name": f"pytest-{tag()}", "template_id": t["id"]}).status_code == 422
    r = sharing(admin, t, "reshare")
    assert r.status_code == 200 and r.json()["share_status"] == "shared"
    assert t["id"] in ids(writer2)


def test_every_sharing_step_is_audited(admin, writer):
    t = shared(writer, admin)
    sharing(admin, t, "unshare")
    entries = admin.get("/audit-logs", params={"entity_type": "report_template"}).json()
    rows = entries["items"] if isinstance(entries, dict) else entries
    steps = [e["detail"]["sharing"] for e in rows
             if str(e.get("entity_id")) == t["id"] and (e.get("detail") or {}).get("sharing")]
    assert sorted(steps) == ["approve", "request", "unshare"]


# --- deleting, access, input --------------------------------------------------------------------

def test_deleting_a_template_leaves_its_reports_alone(admin, writer):
    t = template(writer)
    rep = new_report(writer, template_id=t["id"])
    assert writer.delete(f"/report-templates/{t['id']}").status_code == 204
    assert writer.get(f"/report-templates/{t['id']}").status_code == 404
    kept = writer.get(f"/reports/{rep['id']}").json()
    assert kept["introduction_md"] == BODY["introduction_md"] and len(kept["sections"]) == 2
    other = shared(writer, admin)                                 # admins delete anything
    assert admin.delete(f"/report-templates/{other['id']}").status_code == 204


def test_readers_and_auditors_have_no_access_to_templates(admin, writer, reader, auditor):
    s = shared(writer, admin)
    for c in (reader, auditor):
        assert c.get("/report-templates").status_code == 403
        assert c.get(f"/report-templates/{s['id']}").status_code == 403
        assert c.post("/report-templates", {"name": f"pytest-{tag()}"}).status_code == 403


def test_template_input_is_validated(writer):
    assert writer.post("/report-templates", {"name": "  "}).status_code == 422
    assert writer.post("/report-templates", {"name": "x" * 121}).status_code == 422
    assert writer.post("/report-templates", {"name": "ok", "sections": [{"title": ""}]}).status_code == 422
    t = template(writer)
    assert writer.patch(f"/report-templates/{t['id']}", {"name": "no version"}).status_code == 422
    assert sharing(writer, t, "publish").status_code == 422
    assert writer.post("/reports", {"name": f"pytest-{tag()}", "template_id": "00000000-0000-0000-0000-000000000000"}).status_code == 422
