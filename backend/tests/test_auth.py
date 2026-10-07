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
    assert admin.post("/users", {"username": username, "password": temp, "role": "writer_all"}).status_code == 201
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
    user = make_user(admin, "writer_all")
    assert user.get("/vulnerabilities").status_code == 200
    r = admin.post(f"/users/{user.user['id']}/reset-password", {"new_password": "Reset-By-Admin-1"})
    assert r.status_code == 200
    # Same access token, but the account is flagged again: blocked at once.
    assert user.get("/vulnerabilities").status_code == 403


def test_refresh_token_gives_a_new_access_token(writer):
    tokens = login(writer.user["username"], writer.password).json()
    r = httpx.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert Client(r.json()["access_token"]).get("/auth/me").status_code == 200
    assert httpx.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": "garbage"}).status_code == 401
    # an access token is not a refresh token
    assert httpx.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": tokens["access_token"]}).status_code == 401


def test_deactivated_user_cannot_log_in_or_refresh(admin):
    user = make_user(admin, "writer_all")
    tokens = login(user.user["username"], user.password).json()
    assert admin.patch(f"/users/{user.user['id']}", {"is_active": False}).status_code == 200
    assert login(user.user["username"], user.password).status_code == 401
    assert httpx.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert user.get("/auth/me").status_code == 401  # the old access token stops working too


def test_admin_cannot_lock_themselves_out(admin):
    me = admin.user["id"]
    assert admin.patch(f"/users/{me}", {"is_active": False}).status_code == 400
    assert admin.patch(f"/users/{me}", {"role": "reader_all"}).status_code == 400


def test_duplicate_username_is_a_conflict(admin, writer):
    r = admin.post("/users", {"username": writer.user["username"], "password": "Temp-12345", "role": "reader_all"})
    assert r.status_code == 409


def test_read_only_roles_cannot_write(reader, auditor):
    for c in (reader, auditor):
        assert c.post("/vulnerabilities", {"identifier": "pytest-ro"}).status_code == 403
        assert c.post("/reports", {"name": "pytest-ro"}).status_code == 403
        assert c.get("/vulnerabilities").status_code == 200  # but reading is fine
        assert c.get("/reports").status_code == 200


def test_user_and_key_management_is_admin_only(writer, reader):
    for c in (writer, reader):
        assert c.post("/users", {"username": "pytest-x", "password": "Temp-12345", "role": "reader_all"}).status_code == 403
        assert c.get("/api-keys").status_code == 403
        assert c.post("/api-keys", {"label": "pytest-x", "role": "writer_all"}).status_code == 403


def test_audit_log_is_for_admin_and_auditor_only(admin, auditor, writer, reader):
    assert admin.get("/audit-logs").status_code == 200
    assert auditor.get("/audit-logs").status_code == 200
    assert writer.get("/audit-logs").status_code == 403
    assert reader.get("/audit-logs").status_code == 403


def test_password_changes_and_logins_are_audited(admin):
    user = make_user(admin, "writer_all")
    items = admin.get("/audit-logs", params={"page_size": 200}).json()["items"]
    mine = [e for e in items if e["actor"] == user.user["username"]]
    actions = {e["action"] for e in mine}
    assert "login" in actions and "update" in actions
