"""Authentication, first-login password change, roles."""

import httpx
from conftest import BASE_URL, Client, login, make_user, tag


def test_bad_credentials_are_rejected():
    assert login("admin", "definitely-wrong").status_code == 401
    assert login("nobody-" + tag(), "x").status_code == 401


def test_protected_routes_need_a_token():
    assert httpx.get(f"{BASE_URL}/vulnerabilities").status_code == 401
    assert httpx.get(f"{BASE_URL}/reports").status_code == 401


def test_new_user_must_change_password_before_anything_else(admin):
    username, temp = f"pytest-first-{tag()}", f"Temp-{tag()}-1"
    assert admin.post("/users", {"username": username, "password": temp, "role": "write_all"}).status_code == 201
    c = Client(login(username, temp).json()["access_token"])

    # Everything is blocked, except reading oneself and changing the password.
    blocked = c.get("/vulnerabilities")
    assert blocked.status_code == 403 and blocked.json()["detail"] == "password_change_required"
    assert c.get("/reports").status_code == 403
    me = c.get("/auth/me")
    assert me.status_code == 200 and me.json()["must_change_password"] is True

    # Password rules
    assert c.post("/auth/change-password", {"current_password": "wrong", "new_password": "Another-123"}).status_code == 400
    assert c.post("/auth/change-password", {"current_password": temp, "new_password": "abc"}).status_code == 400
    assert c.post("/auth/change-password", {"current_password": temp, "new_password": temp}).status_code == 400
    assert c.post("/auth/change-password", {"current_password": temp, "new_password": "Brand-New-9"}).status_code == 204

    # ... and the gate lifts immediately, without logging in again.
    assert c.get("/vulnerabilities").status_code == 200
    assert c.get("/auth/me").json()["must_change_password"] is False


def test_admin_reset_locks_an_already_open_session(admin):
    user = make_user(admin, "write_all")
    assert user.get("/vulnerabilities").status_code == 200
    r = admin.post(f"/users/{user.user['id']}/reset-password", {"new_password": "Reset-By-Admin-1"})
    assert r.status_code == 200
    # A reset ends every open session at once (D16).
    assert user.get("/vulnerabilities").status_code == 401


def test_refresh_token_gives_a_new_access_token(writer):
    tokens = login(writer.user["username"], writer.password).json()
    r = httpx.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert Client(r.json()["access_token"]).get("/auth/me").status_code == 200
    assert httpx.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": "garbage"}).status_code == 401
    # an access token is not a refresh token
    assert httpx.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": tokens["access_token"]}).status_code == 401


def test_deactivated_user_cannot_log_in_or_refresh(admin):
    user = make_user(admin, "write_all")
    tokens = login(user.user["username"], user.password).json()
    assert admin.patch(f"/users/{user.user['id']}", {"is_active": False}).status_code == 200
    assert login(user.user["username"], user.password).status_code == 401
    assert httpx.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert user.get("/auth/me").status_code == 401  # the old access token stops working too


def test_admin_cannot_lock_themselves_out(admin):
    me = admin.user["id"]
    assert admin.patch(f"/users/{me}", {"is_active": False}).status_code == 400
    assert admin.patch(f"/users/{me}", {"role": "read_all"}).status_code == 400


def test_duplicate_username_is_a_conflict(admin, writer):
    r = admin.post("/users", {"username": writer.user["username"], "password": "Temp-12345", "role": "read_all"})
    assert r.status_code == 409


def test_read_only_roles_cannot_write(reader, auditor):
    for c in (reader, auditor):
        assert c.post("/vulnerabilities", {"identifier": "pytest-ro"}).status_code == 403
        assert c.post("/reports", {"name": "pytest-ro"}).status_code == 403
        assert c.get("/vulnerabilities").status_code == 200  # but reading is fine
        assert c.get("/reports").status_code == 200


def test_user_and_key_management_is_admin_only(writer, reader):
    for c in (writer, reader):
        assert c.post("/users", {"username": "pytest-x", "password": "Temp-12345", "role": "read_all"}).status_code == 403
        assert c.get("/api-keys").status_code == 403
        assert c.post("/api-keys", {"label": "pytest-x", "scopes": ["vulns:write"]}).status_code == 403


def test_audit_log_is_for_admin_and_auditor_only(admin, auditor, writer, reader):
    assert admin.get("/audit-logs").status_code == 200
    assert auditor.get("/audit-logs").status_code == 200
    assert writer.get("/audit-logs").status_code == 403
    assert reader.get("/audit-logs").status_code == 403


def test_password_changes_and_logins_are_audited(admin):
    user = make_user(admin, "write_all")
    items = admin.get("/audit-logs", params={"page_size": 200}).json()["items"]
    mine = [e for e in items if e["actor"] == user.user["username"]]
    actions = {e["action"] for e in mine}
    assert "login" in actions and "update" in actions


def _forged_refresh(user, started_min_ago: int, issued_min_ago: int, life_min: int) -> str:
    """The refresh token of a real session, as the server would have signed it in the past."""
    from datetime import UTC, datetime, timedelta

    import jwt

    from app.config import settings

    now = datetime.now(UTC)
    live = login(user.user["username"], user.password).json()["refresh_token"]
    claims = jwt.decode(live, options={"verify_signature": False})
    payload = {
        "sub": user.user["id"], "type": "refresh", "sid": claims["sid"], "jti": claims["jti"],
        "sst": int((now - timedelta(minutes=started_min_ago)).timestamp()),
        "iat": now - timedelta(minutes=issued_min_ago),
        "exp": now - timedelta(minutes=issued_min_ago) + timedelta(minutes=life_min),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def test_session_lasts_one_hour_and_refresh_never_extends_it(writer):
    from datetime import datetime

    tokens = login(writer.user["username"], writer.password).json()
    end = datetime.fromisoformat(tokens["session_expires_at"])
    assert tokens["idle_timeout_seconds"] == 15 * 60
    r = httpx.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert datetime.fromisoformat(r.json()["session_expires_at"]) == end      # same end
    assert r.json()["refresh_token"] != tokens["refresh_token"]              # rotated: idle window restarts

    # a session that began 61 minutes ago cannot be renewed, even with a live refresh token
    stale = _forged_refresh(writer, started_min_ago=61, issued_min_ago=1, life_min=15)
    assert httpx.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": stale}).status_code == 401
    # a session started 30 minutes ago is still renewable
    ok = _forged_refresh(writer, started_min_ago=30, issued_min_ago=1, life_min=15)
    assert httpx.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": ok}).status_code == 200


def test_idle_session_cannot_be_renewed(writer):
    # last renewed 16 minutes ago: the refresh token (15 min) is dead
    idle = _forged_refresh(writer, started_min_ago=20, issued_min_ago=16, life_min=15)
    assert httpx.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": idle}).status_code == 401


def refresh(token: str) -> httpx.Response:
    return httpx.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": token})


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_failed_logins_are_audited_and_the_account_is_blocked_for_a_while(admin, writer):
    name = "nobody-" + tag()
    for _ in range(5):
        assert login(name, "wrong").status_code == 401
    assert login(name, "wrong").status_code == 429
    entries = admin.get("/audit-logs", params={"action": "login_failed", "page_size": 20}).json()["items"]
    assert sum(e["actor"] == name for e in entries) == 5


def test_a_success_clears_the_failures_of_the_account(writer):
    name = writer.user["username"]
    for _ in range(4):
        login(name, "wrong")
    assert login(name, writer.password).status_code == 200
    assert login(name, "wrong").status_code == 401
    assert login(name, writer.password).status_code == 200


def test_logout_ends_the_session_for_every_token(writer):
    tokens = login(writer.user["username"], writer.password).json()
    assert httpx.post(f"{BASE_URL}/auth/logout", headers=bearer(tokens["access_token"])).status_code == 204
    assert httpx.get(f"{BASE_URL}/auth/me", headers=bearer(tokens["access_token"])).status_code == 401
    assert refresh(tokens["refresh_token"]).status_code == 401


def test_a_replayed_refresh_token_ends_the_session(writer, monkeypatch):
    from datetime import timedelta

    from sqlalchemy import update

    from app.db import SessionLocal
    from app.models.user import AuthSession

    first = login(writer.user["username"], writer.password).json()
    second = refresh(first["refresh_token"]).json()
    assert refresh(first["refresh_token"]).status_code == 200    # tabs racing: tolerated briefly
    with SessionLocal() as s:
        s.execute(update(AuthSession).where(AuthSession.user_id == writer.user["id"])
                  .values(rotated_at=AuthSession.rotated_at - timedelta(minutes=5)))
        s.commit()
    assert refresh(first["refresh_token"]).status_code == 401     # a replay
    assert refresh(second["refresh_token"]).status_code == 401    # and the whole session died


def test_a_password_change_ends_the_other_sessions(admin):
    from conftest import make_user

    user = make_user(admin, "read_all")
    other = login(user.user["username"], user.password).json()
    assert user.post("/auth/change-password", {"current_password": user.password,
                                               "new_password": "another-pass-1"}).status_code == 204
    assert httpx.get(f"{BASE_URL}/auth/me", headers=bearer(other["access_token"])).status_code == 401
    assert user.get("/auth/me").status_code == 200                # the session that changed it stays


def test_a_password_over_72_bytes_is_refused_not_a_crash(admin):
    body = {"username": "pytest-long-" + tag(), "password": "x" * 73, "role": "read_all"}
    assert admin.post("/users", body).status_code == 422


def test_reading_a_vulnerability_is_audited(admin, writer):
    from conftest import new_vuln

    v = new_vuln(writer, identifier="pytest-read-" + tag())
    writer.get(f"/vulnerabilities/{v['id']}")
    entries = admin.get("/audit-logs", params={"action": "read", "entity_type": "vulnerability"}).json()["items"]
    assert any(e["entity_id"] == v["id"] for e in entries)
