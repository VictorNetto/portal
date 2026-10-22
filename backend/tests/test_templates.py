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
