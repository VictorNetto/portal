"""The server enforces the same input rules as the form (any client can call the API)."""

from conftest import make_user, new_vuln, tag


def test_references_must_be_http_urls(writer):
    for bad in ("not a url", "javascript:alert(1)", "ftp://x.example/a"):
        r = writer.post("/vulnerabilities", {"identifier": f"pytest-{tag()}", "references": [bad]})
        assert r.status_code == 422, bad
    v = new_vuln(writer, references=["  https://owasp.org/x  ", ""])
    assert v["references"] == ["https://owasp.org/x"]  # trimmed, blanks dropped
    r = writer.patch(f"/vulnerabilities/{v['id']}", {"version": v["version"], "references": ["nope"]})
    assert r.status_code == 422


def test_cwe_is_normalised_or_refused(writer):
    assert new_vuln(writer, cwe="79")["cwe"] == "CWE-79"
    assert new_vuln(writer, cwe="cwe-89")["cwe"] == "CWE-89"
    assert writer.post("/vulnerabilities", {"identifier": f"pytest-{tag()}", "cwe": "banana"}).status_code == 422
    assert writer.post("/vulnerabilities", {"identifier": f"pytest-{tag()}", "cwe": "CWE-1234567"}).status_code == 422


def test_text_fields_have_limits(writer):
    assert writer.post("/vulnerabilities", {"identifier": "pytest-" + "x" * 600}).status_code == 422
    assert writer.post("/vulnerabilities", {"identifier": f"pytest-{tag()}", "description": "x" * 100_001}).status_code == 422
    assert writer.post("/vulnerabilities", {"identifier": f"pytest-{tag()}", "references": [f"https://e.x/{i}" for i in range(51)]}).status_code == 422


def test_inactive_users_cannot_be_newly_assigned_but_stay_where_they_are(admin, writer):
    gone = make_user(admin, "write_all")
    v = new_vuln(writer, operator_ids=[gone.user["id"]], viewer_ids=[gone.user["id"]])
    assert admin.patch(f"/users/{gone.user['id']}", {"is_active": False}).status_code == 200
    # a new assignment of a deactivated account is refused...
    r = writer.post("/vulnerabilities", {"identifier": f"pytest-{tag()}", "operator_ids": [gone.user["id"]]})
    assert r.status_code == 422 and "Inactive" in r.json()["detail"]
    assert writer.post("/vulnerabilities", {"identifier": f"pytest-{tag()}", "viewer_ids": [gone.user["id"]]}).status_code == 422
    # ...but saving a record that already lists it keeps working
    r = writer.patch(f"/vulnerabilities/{v['id']}", {
        "version": v["version"], "description": "still editable",
        "operator_ids": [gone.user["id"]], "viewer_ids": [gone.user["id"]],
    })
    assert r.status_code == 200, r.text


def test_an_empty_patch_changes_nothing(writer):
    v = new_vuln(writer)
    r = writer.patch(f"/vulnerabilities/{v['id']}", {"version": v["version"], "rvs_id": "X", "status": "fixed"})
    assert r.status_code == 200
    assert r.json()["version"] == v["version"] and r.json()["status"] == "draft" and r.json()["rvs_id"] is None
