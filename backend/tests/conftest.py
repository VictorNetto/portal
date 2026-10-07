"""Integration-test fixtures.

These tests drive the real API over HTTP (the server running in this container on
:8000) and talk to the same dev database for setup/cleanup. Run them with:

    docker compose exec api pip install -e '.[dev]'     # once
    docker compose exec api pytest tests -q

Every record a test creates is named `pytest-...` and is cleaned up (soft-deleted /
deactivated / revoked) when the session ends, so the dev data stays tidy.
"""

import os
import uuid

import httpx
import pytest
from sqlalchemy import text

from app.db import SessionLocal

BASE_URL = os.environ.get("TEST_API_URL", "http://localhost:8000")
ADMIN_USER = os.environ.get("TEST_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "12345678")


class Client:
    """A thin authenticated HTTP client."""

    def __init__(self, token: str | None = None, user: dict | None = None):
        self.http = httpx.Client(base_url=BASE_URL, timeout=120)
        self.token = token
        self.user = user or {}

    def request(self, method: str, path: str, **kw) -> httpx.Response:
        headers = kw.pop("headers", {}) or {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return self.http.request(method, path, headers=headers, **kw)

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, json=None, **kw):
        return self.request("POST", path, json=json, **kw)

    def patch(self, path, json=None, **kw):
        return self.request("PATCH", path, json=json, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)


def login(username: str, password: str) -> httpx.Response:
    return httpx.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password}, timeout=60)


def tag() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    with SessionLocal() as s:
        s.execute(text(
            "UPDATE vulnerabilities SET deleted_at = now() WHERE deleted_at IS NULL AND ("
            "identifier LIKE 'pytest-%' OR created_by IN (SELECT id FROM users WHERE username LIKE 'pytest-%'))"
        ))
        s.execute(text(
            "UPDATE reports SET deleted_at = now(), lock_user_id = NULL WHERE deleted_at IS NULL AND ("
            "name LIKE 'pytest-%' OR created_by IN (SELECT id FROM users WHERE username LIKE 'pytest-%'))"
        ))
        s.execute(text("UPDATE api_keys SET revoked_at = now() WHERE revoked_at IS NULL AND label LIKE 'pytest-%'"))
        s.execute(text("UPDATE users SET is_active = false WHERE username LIKE 'pytest-%'"))
        s.commit()


@pytest.fixture(scope="session")
def admin() -> Client:
    r = login(ADMIN_USER, ADMIN_PASSWORD)
    assert r.status_code == 200, f"cannot log in as {ADMIN_USER}: {r.text}"
    me = Client(r.json()["access_token"])
    me.user = me.get("/auth/me").json()
    return me


def make_user(admin: Client, role: str) -> Client:
    """Create a user the way a real one starts: temp password, forced change, then log in."""
    username = f"pytest-{role}-{tag()}"
    temp, final = f"Temp-{tag()}-1", f"Final-{tag()}-1"
    r = admin.post("/users", {"username": username, "password": temp, "role": role})
    assert r.status_code == 201, r.text
    user = r.json()
    first = Client(login(username, temp).json()["access_token"])
    assert first.post("/auth/change-password", {"current_password": temp, "new_password": final}).status_code == 204
    client = Client(login(username, final).json()["access_token"], user)
    client.password = final
    return client


@pytest.fixture(scope="session")
def writer(admin) -> Client:
    return make_user(admin, "writer_all")


@pytest.fixture(scope="session")
def writer2(admin) -> Client:
    return make_user(admin, "writer_all")


@pytest.fixture(scope="session")
def reader(admin) -> Client:
    return make_user(admin, "reader_all")


@pytest.fixture(scope="session")
def auditor(admin) -> Client:
    return make_user(admin, "auditor")


# --- builders ---------------------------------------------------------------

def new_vuln(c: Client, **fields) -> dict:
    body = {"identifier": f"pytest-{tag()}", "description": "d", "finding_detail": "f", "mitigation": "m", **fields}
    r = c.post("/vulnerabilities", body)
    assert r.status_code == 201, r.text
    return r.json()


def saved_vuln(c: Client, **fields) -> dict:
    v = new_vuln(c, **fields)
    r = c.post(f"/vulnerabilities/{v['id']}/send")
    assert r.status_code == 200, r.text
    return r.json()


def acknowledged_vuln(c: Client, **fields) -> dict:
    v = saved_vuln(c, **fields)
    assert c.post(f"/vulnerabilities/{v['id']}/dispatch").status_code == 200
    r = c.post(f"/vulnerabilities/{v['id']}/rvs", {"rvs_id": f"RVS-pytest-{tag()}"})
    assert r.status_code == 200, r.text
    return r.json()


def new_report(c: Client, **fields) -> dict:
    r = c.post("/reports", {"name": f"pytest-{tag()}", **fields})
    assert r.status_code == 201, r.text
    return r.json()


def report_vuln(c: Client, report_id: str, **fields) -> dict:
    body = {"identifier": f"pytest-{tag()}", "description": "d", **fields}
    r = c.post(f"/reports/{report_id}/vulnerabilities", body)
    assert r.status_code == 201, r.text
    return r.json()


def png_bytes() -> bytes:
    import struct
    import zlib

    raw = b"".join(b"\x00" + bytes([30, 120, 220]) * 20 for _ in range(10))

    def chunk(t: bytes, d: bytes) -> bytes:
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 20, 10, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def upload(c: Client, path: str, name: str, data: bytes, display_name: str | None = None) -> httpx.Response:
    return c.post(path, files={"file": (name, data)}, data={"display_name": display_name} if display_name else None)
