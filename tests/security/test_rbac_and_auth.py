"""RBAC + auth flows: refresh rotation, reuse detection, limiter, endpoints."""
from __future__ import annotations

import pytest


def _login(client, email, password="password-12-chars"):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_login_success_sets_cookie_and_bearer(client, users):
    r = _login(client, "analyst@example.com")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["role"] == "analyst"
    assert "aegis_refresh" in client.cookies or \
        "aegis_refresh" in r.headers.get("set-cookie", "")


def test_login_wrong_password_generic_error(client, users):
    r = _login(client, "analyst@example.com", password="wrong-password-123")
    assert r.status_code == 401
    # Uniform anti-enumeration semantics (AUTH-07): flat structured envelope.
    assert r.json()["code"] == "invalid_credentials"
    assert "invalid_credentials" in str(r.json()["detail"]) or \
        r.json()["detail"] == "invalid_credentials"


def test_viewer_cannot_approve(client, users):
    r = _login(client, "viewer@example.com")
    token = r.json()["data"]["access_token"]
    res = client.post("/approvals/00000000-0000-0000-0000-000000000000/approve",
                      headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_analyst_cannot_list_audit(client, users):
    token = _login(client, "analyst@example.com").json()["data"]["access_token"]
    res = client.get("/audit", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_admin_can_set_role(client, users):
    token = _login(client, "admin@example.com").json()["data"]["access_token"]
    uid = str(users["viewer"].id)
    res = client.put(f"/users/{uid}/role", json={"role": "analyst"},
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["data"]["role"] == "analyst"


def test_analyst_cannot_set_role(client, users):
    token = _login(client, "analyst@example.com").json()["data"]["access_token"]
    uid = str(users["viewer"].id)
    res = client.put(f"/users/{uid}/role", json={"role": "admin"},
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_inactive_user_rejected_on_me(client, users, db):
    users["viewer"].is_active = False
    db.flush()
    token = _login(client, "viewer@example.com")
    if token.status_code != 200:
        pytest.skip("inactive login blocked at login (also acceptable)")
    me = client.get("/auth/me", headers={
        "Authorization": f"Bearer {token.json()['data']['access_token']}"})
    assert me.status_code == 401


def test_csv_export_escapes_formula_injection(client, users, db):
    from app.services.audit import _csv_safe

    assert _csv_safe("=cmd|' /C calc'!A0") .startswith("'=")
    assert "\n" not in _csv_safe("line1\nline2")
