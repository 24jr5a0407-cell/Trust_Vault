import pytest
from config import ADMIN_EMAIL, ADMIN_DEFAULT_PASSWORD

def test_admin_routes_forbidden_for_regular_users(client, user_headers):
    # Regular user attempting admin endpoints should receive HTTP 403 Forbidden
    routes = [
        ("GET", "/api/admin/requests"),
        ("GET", "/api/admin/users"),
        ("GET", "/api/admin/documents"),
        ("GET", "/api/admin/ledger"),
        ("GET", "/api/admin/ledger/export"),
        ("POST", "/api/admin/approve"),
        ("DELETE", "/api/admin/users/test@example.com")
    ]
    for method, path in routes:
        if method == "GET":
            res = client.get(path, headers=user_headers)
        elif method == "POST":
            res = client.post(path, json={"email": "test@example.com", "status": "APPROVED"}, headers=user_headers)
        elif method == "DELETE":
            res = client.delete(path, headers=user_headers)
        assert res.status_code == 403, f"Expected 403 Forbidden on {method} {path}, got {res.status_code}"

def test_admin_routes_allowed_for_admin(client, admin_headers):
    # Admin can list requests
    res = client.get("/api/admin/requests", headers=admin_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # Admin can list users
    res_users = client.get("/api/admin/users", headers=admin_headers)
    assert res_users.status_code == 200
    users = res_users.json()
    assert any(u["email"] == ADMIN_EMAIL for u in users)

    # Admin can export ledger
    res_export = client.get("/api/admin/ledger/export", headers=admin_headers)
    assert res_export.status_code == 200
    assert "text/csv" in res_export.headers.get("Content-Type", "")

def test_cannot_delete_primary_admin(client, admin_headers):
    res = client.delete(f"/api/admin/users/{ADMIN_EMAIL}", headers=admin_headers)
    assert res.status_code == 400
    assert "Cannot remove primary admin" in res.json()["detail"]
