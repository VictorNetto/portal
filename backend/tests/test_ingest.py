"""Creating vulnerabilities through the integration API (POST /v1/vulnerabilities)."""

import httpx
import pytest
from conftest import BASE_URL, tag

URL = f"{BASE_URL}/v1/vulnerabilities"


def make_key(admin, scopes=("vulns:write",), **extra):
    r = admin.post("/api-keys", {"label": f"pytest-{tag()}", "scopes": list(scopes), **extra})
    assert r.status_code == 201, r.text
    return r.json()


def post(key, payload, **kw):
    headers = {"X-API-Key": key["plaintext"]} if key else {}
    return httpx.post(URL, json=payload, headers=headers, timeout=60, **kw)


@pytest.fixture(scope="module")
def key(admin):
    return make_key(admin)


def test_plaintext_is_shown_once_only(admin, key):
    assert key["plaintext"] and key["key_prefix"] == key["plaintext"][:8]
    listed = next(k for k in admin.get("/api-keys").json() if k["id"] == key["id"])
    assert "plaintext" not in listed and "key_hash" not in listed


def test_authentication_failures_are_indistinguishable(admin, key):
    revoked = make_key(admin)
    admin.post(f"/api-keys/{revoked['id']}/revoke")
    expired = make_key(admin, expires_at="2020-01-01T00:00:00")
    responses = [post(None, {"identifier": "x"}), post({"plaintext": "wrong"}, {"identifier": "x"}),
                 post(revoked, {"identifier": "x"}), post(expired, {"identifier": "x"})]
    assert all(r.status_code == 401 for r in responses)
    assert len({r.text for r in responses}) == 1            # same message: no hint about which keys exist


def test_the_old_ingest_path_is_gone(key):
    r = httpx.post(f"{BASE_URL}/ingest/vulnerabilities", json={"identifier": "x"}, headers={"X-API-Key": key["plaintext"]})
    assert r.status_code == 404


def test_keys_do_not_work_on_the_ui_endpoints(key):
    headers = {"X-API-Key": key["plaintext"]}
    for path in ("/vulnerabilities", "/users", "/reports", "/audit-logs", "/api-keys"):
        assert httpx.get(f"{BASE_URL}{path}", headers=headers).status_code == 401


def test_a_user_session_is_not_an_api_key(writer):
    r = httpx.post(URL, json={"identifier": "x"}, headers={"Authorization": f"Bearer {writer.token}"})
    assert r.status_code == 401


def test_only_keys_with_vulns_write_can_ingest(admin):
    r = post(make_key(admin, ["vulns:read", "reports:read", "exports", "rvs:write"]), {"identifier": "pytest-x"})
    assert r.status_code == 403 and "vulns:write" in r.json()["detail"]


def test_creates_a_draft_by_default(admin, writer, key):
    ident = f"pytest-{tag()}"
    r = post(key, {"identifier": ident, "source": "nuclei", "cwe": "527", "cvss_score": 5.3,
                   "references": ["https://example.com/a"], "operators": [writer.user["username"]],
                   "metadata": {"template": "git-config"}, "scan_id": "SC-1"})
    assert r.status_code == 201
    out = r.json()
    assert out["status"] == "draft" and out["internal_id"] is None
    v = admin.get(f"/vulnerabilities/{out['id']}").json()
    assert v["cwe"] == "CWE-527" and v["source"] == "nuclei"                      # CWE normalised
    assert [o["username"] for o in v["operators"]] == [writer.user["username"]]   # operators by username
    assert v["references"] == ["https://example.com/a"]


def test_extra_fields_are_kept_as_metadata(key):
    from sqlalchemy import text

    from app.db import SessionLocal

    r = post(key, {"identifier": f"pytest-{tag()}", "metadata": {"host": "a.example"}, "scan_id": "SC-9"})
    with SessionLocal() as s:
        meta = s.execute(text("SELECT extra_metadata FROM vulnerabilities WHERE id = :i"), {"i": r.json()["id"]}).scalar_one()
    assert meta == {"host": "a.example", "scan_id": "SC-9"}


def test_ready_needs_the_ui_required_fields_and_gets_an_id(key):
    full = {"identifier": f"pytest-{tag()}", "description": "d", "finding_detail": "f", "mitigation": "m", "status": "ready"}
    r = post(key, full)
    assert r.status_code == 201 and r.json()["status"] == "ready" and r.json()["internal_id"].startswith("VULN-")
    partial = post(key, {"identifier": f"pytest-{tag()}", "status": "ready"})
    assert partial.status_code == 422 and "description" in partial.json()["detail"]


def test_cannot_ingest_beyond_ready(key):
    assert post(key, {"identifier": "pytest-x", "status": "sent"}).status_code == 422
    assert post(key, {"identifier": "pytest-x", "status": "fixing"}).status_code == 422
    assert post(key, {"identifier": "pytest-x", "status": "saved_local"}).status_code == 422


@pytest.mark.parametrize("payload", [
    {"source": "nmap"},                                         # nothing meaningful
    {"identifier": "pytest-x", "cvss_score": 11},
    {"identifier": "pytest-x", "cwe": "not-a-cwe"},
    {"identifier": "pytest-x", "references": ["javascript:alert(1)"]},
    {"identifier": "pytest-x", "operators": ["no-such-user"]},
    {"identifier": "pytest-x", "metadata": {"blob": "A" * 70_000}},
])
def test_invalid_payloads_are_rejected(key, payload):
    assert post(key, payload).status_code == 422


def test_body_size_and_json_errors(key):
    big = b'{"identifier": "' + b"A" * (1024 * 1024 + 10) + b'"}'
    r = httpx.post(URL, content=big, headers={"X-API-Key": key["plaintext"], "Content-Type": "application/json"})
    assert r.status_code == 413
    r = httpx.post(URL, content=b"not json", headers={"X-API-Key": key["plaintext"], "Content-Type": "application/json"})
    assert r.status_code == 422


def test_the_key_is_the_audit_actor_and_usage_is_tracked(admin, key):
    post(key, {"identifier": f"pytest-{tag()}"})
    items = admin.get("/audit-logs", params={"action": "create", "page_size": 50}).json()["items"]
    assert any(e["actor"] == f"api:{key['key_prefix']}" for e in items)
    assert next(k for k in admin.get("/api-keys").json() if k["id"] == key["id"])["last_used_at"]
