"""Integration API (/v1): API keys with scopes (D13)."""

import httpx
import pytest
from conftest import (
    BASE_URL,
    fixing_vuln,
    new_report,
    new_vuln,
    png_bytes,
    report_vuln,
    saved_vuln,
    tag,
    upload,
)

ALL = ["vulns:read", "vulns:write", "rvs:write", "reports:read", "exports"]


def make_key(admin, scopes):
    r = admin.post("/api-keys", {"label": f"pytest-{tag()}", "scopes": scopes})
    assert r.status_code == 201, r.text
    return r.json()["plaintext"]


def call(key, method, path, **kw):
    return httpx.request(method, f"{BASE_URL}/v1{path}", headers={"X-API-Key": key}, timeout=60, **kw)


@pytest.fixture(scope="module")
def full(admin):
    return make_key(admin, ALL)


def sent_vuln(c):
    v = saved_vuln(c)
    assert c.post(f"/vulnerabilities/{v['id']}/send").status_code == 200
    return v


# --- keys and scopes ---------------------------------------------------------

def test_scopes_are_validated_when_a_key_is_created(admin):
    assert admin.post("/api-keys", {"label": "pytest-x", "scopes": []}).status_code == 422
    assert admin.post("/api-keys", {"label": "pytest-x", "scopes": ["users:write"]}).status_code == 422
    r = admin.post("/api-keys", {"label": f"pytest-{tag()}", "scopes": ["exports", "vulns:read", "exports"]})
    assert r.status_code == 201 and r.json()["scopes"] == ["exports", "vulns:read"]


def test_every_endpoint_needs_its_scope(admin, writer):
    v = new_vuln(writer)
    rep = new_report(writer)
    none = make_key(admin, ["vulns:write"])                 # a key with only an unrelated scope
    for method, path in [
        ("GET", "/vulnerabilities"), ("GET", f"/vulnerabilities/{v['id']}"),
        ("GET", f"/vulnerabilities/{v['id']}/attachments"), ("GET", f"/vulnerabilities/{v['id']}/export"),
        ("POST", f"/vulnerabilities/{v['id']}/rvs"), ("GET", "/rvs-queue"),
        ("GET", "/reports"), ("GET", f"/reports/{rep['id']}"), ("GET", f"/reports/{rep['id']}/export"),
    ]:
        r = call(none, method, path, json={"rvs_id": "x"} if method == "POST" else None)
        assert r.status_code == 403, (path, r.status_code)
        assert "lacks the scope" in r.json()["detail"]
    assert call("wrong", "GET", "/vulnerabilities").status_code == 401
    assert httpx.get(f"{BASE_URL}/v1/vulnerabilities", headers={"Authorization": f"Bearer {writer.token}"}).status_code == 401


def test_keys_still_cannot_reach_the_ui_endpoints(full):
    for path in ("/vulnerabilities", "/reports", "/users", "/audit-logs", "/api-keys"):
        assert httpx.get(f"{BASE_URL}{path}", headers={"X-API-Key": full}).status_code == 401


# --- vulnerabilities -------------------------------------------------------------

def test_read_a_vulnerability_by_uuid_or_number_without_internal_notes(full, writer):
    v = saved_vuln(writer, internal_notes="segredo interno", cvss_score=7.5, source="nuclei",
                   operator_ids=[writer.user["id"]])
    by_id = call(full, "GET", f"/vulnerabilities/{v['id']}").json()
    by_number = call(full, "GET", f"/vulnerabilities/{v['internal_id'].lower()}").json()
    assert by_id == by_number
    assert by_id["internal_id"] == v["internal_id"] and by_id["status"] == "ready"
    assert by_id["operators"] == [writer.user["username"]]
    assert "internal_notes" not in by_id and "segredo" not in str(by_id)
    assert call(full, "GET", "/vulnerabilities/VULN-999999").status_code == 404


def test_list_filters_and_pages_in_update_order(full, writer):
    src = f"pytest-src-{tag()}"
    made = [new_vuln(writer, source=src, cvss_score=s) for s in (3, 6, 9)]
    page = call(full, "GET", "/vulnerabilities", params={"source": src}).json()
    assert [x["id"] for x in page["items"]] == [m["id"] for m in made] and page["next_cursor"] is None
    hi = call(full, "GET", "/vulnerabilities", params={"source": src, "cvss_min": 6}).json()["items"]
    assert len(hi) == 2
    assert call(full, "GET", "/vulnerabilities", params={"source": src, "status": "fixed"}).json()["items"] == []

    seen, cursor = [], None
    while True:
        p = call(full, "GET", "/vulnerabilities", params={"source": src, "limit": 1, **({"cursor": cursor} if cursor else {})}).json()
        seen += [x["id"] for x in p["items"]]
        cursor = p["next_cursor"]
        if not cursor:
            break
    assert seen == [m["id"] for m in made]
    assert call(full, "GET", "/vulnerabilities", params={"cursor": "garbage"}).status_code == 422


def test_updated_since_returns_what_changed(full, writer):
    src = f"pytest-sync-{tag()}"
    old = new_vuln(writer, source=src)
    changed = new_vuln(writer, source=src)
    mark = call(full, "GET", f"/vulnerabilities/{changed['id']}").json()["updated_at"]
    assert writer.patch(f"/vulnerabilities/{changed['id']}", {"version": changed["version"], "cvss_score": 4}).status_code == 200
    items = call(full, "GET", "/vulnerabilities", params={"source": src, "updated_since": mark}).json()["items"]
    assert [x["id"] for x in items] == [changed["id"]]
    assert old["id"] not in [x["id"] for x in items]
    with_z = call(full, "GET", "/vulnerabilities", params={"source": src, "updated_since": mark + "Z"}).json()["items"]
    assert [x["id"] for x in with_z] == [changed["id"]]                  # an ISO time in UTC with "Z" works too


def test_set_rvs_through_the_queue(admin, full, writer):
    v = sent_vuln(writer)
    queue = [x["id"] for x in call(full, "GET", "/rvs-queue").json()]
    assert v["id"] in queue
    rvs_only = make_key(admin, ["rvs:write"])                      # a ticketing system needs nothing else
    r = call(rvs_only, "POST", f"/vulnerabilities/{v['internal_id']}/rvs", json={"rvs_id": "RVS-pytest-1"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "fixing" and r.json()["rvs_id"] == "RVS-pytest-1"
    assert v["id"] not in [x["id"] for x in call(rvs_only, "GET", "/rvs-queue").json()]
    again = call(rvs_only, "POST", f"/vulnerabilities/{v['id']}/rvs", json={"rvs_id": "RVS-2"})
    assert again.status_code == 409                                  # immutable once set
    draft = new_vuln(writer)
    assert call(rvs_only, "POST", f"/vulnerabilities/{draft['id']}/rvs", json={"rvs_id": "x"}).status_code == 409
    rows = admin.get("/audit-logs", params={"action": "status_change", "page_size": 200}).json()["items"]
    assert any(x["entity_id"] == v["id"] and x["actor"].startswith("api:") for x in rows)   # the key is the actor


def test_exports_and_evidence(admin, full, writer):
    v = fixing_vuln(writer)
    up = upload(writer, f"/vulnerabilities/{new_vuln(writer)['id']}/attachments", "shot.png", png_bytes())
    assert up.status_code == 201, up.text
    pdf = call(full, "GET", f"/vulnerabilities/{v['id']}/export")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    assert "attachment" in pdf.headers["content-disposition"]
    docx = call(full, "GET", f"/vulnerabilities/{v['id']}/export", params={"format": "docx"})
    assert docx.status_code == 200 and docx.content[:2] == b"PK"
    assert call(full, "GET", f"/vulnerabilities/{v['id']}/export", params={"format": "xlsx"}).status_code == 422

    att = up.json()
    owner = att["vulnerability_id"]
    listed = call(full, "GET", f"/vulnerabilities/{owner}/attachments").json()
    assert [a["id"] for a in listed] == [att["id"]]
    content = call(full, "GET", f"/attachments/{att['id']}/content")
    assert content.status_code == 200 and content.content == png_bytes()
    reports_only = make_key(admin, ["reports:read"])                  # vulnerability evidence needs vulns:read
    assert call(reports_only, "GET", f"/attachments/{att['id']}/content").status_code == 404


# --- reports ---------------------------------------------------------------------

def test_read_and_export_a_report(full, writer):
    rep = new_report(writer, client_name=f"pytest-client-{tag()}")
    assert writer.post(f"/reports/{rep['id']}/lock").status_code == 200
    assert writer.patch(f"/reports/{rep['id']}", {"internal_notes": "não sai"}).status_code == 200
    assert writer.post(f"/reports/{rep['id']}/sections", {"title": "Metodologia", "content_markdown": "OWASP"}).status_code == 201
    rv = report_vuln(writer, rep["id"])

    got = call(full, "GET", f"/reports/{rep['internal_id']}").json()
    assert got["id"] == rep["id"] and got["status"] == "draft" and got["vulnerability_count"] == 1
    assert [s["title"] for s in got["sections"]] == ["Metodologia"]
    assert [x["id"] for x in got["vulnerabilities"]] == [rv["id"]]
    assert "internal_notes" not in got and "não sai" not in str(got)

    listed = call(full, "GET", "/reports", params={"client": rep["client_name"]}).json()["items"]
    assert [x["id"] for x in listed] == [rep["id"]]
    in_report = call(full, "GET", "/vulnerabilities", params={"report": rep["id"]}).json()["items"]
    assert [x["id"] for x in in_report] == [rv["id"]] and in_report[0]["report"]["id"] == rep["id"]

    for fmt, magic in (("pdf", b"%PDF"), ("xlsx", b"PK"), ("docx", b"PK")):
        r = call(full, "GET", f"/reports/{rep['id']}/export", params={"format": fmt})
        assert r.status_code == 200 and r.content[:len(magic)] == magic, fmt


def test_create_through_v1(full):
    r = call(full, "POST", "/vulnerabilities", json={"identifier": f"pytest-{tag()}", "source": "v1"})
    assert r.status_code == 201 and r.json()["status"] == "draft"
