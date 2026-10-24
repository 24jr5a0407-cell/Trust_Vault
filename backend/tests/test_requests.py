import io
import pytest

def register_user(client, admin_headers, email, password):
    client.post("/api/request-access", json={"email": email})
    approve_res = client.post("/api/admin/approve", json={"email": email, "status": "APPROVED"}, headers=admin_headers)
    code = approve_res.json()["secure_code"]
    client.post("/api/register", json={"email": email, "password": password, "secure_code": code})

def test_document_request_lifecycle(client, admin_headers, user_headers, bob_headers):
    register_user(client, admin_headers, "alice@trustvault.com", "Password123")
    register_user(client, admin_headers, "bob@trustvault.com", "Password123")

    # Alice uploads document
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("project_plan.pdf", io.BytesIO(b"%PDF-1.4\nProject Plan Details"), "application/pdf")},
        headers=user_headers
    )
    doc_id = upload_res.json()["document_id"]

    # Bob requests access to Alice's document
    req_res = client.post(f"/api/documents/{doc_id}/request-access", headers=bob_headers)
    assert req_res.status_code == 200

    # Bob requests access AGAIN -> should return clean 400 without crashing generator
    dup_res = client.post(f"/api/documents/{doc_id}/request-access", headers=bob_headers)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

    # Bob checks his requests
    my_reqs = client.get("/api/documents/my-requests", headers=bob_headers)
    assert my_reqs.status_code == 200
    assert len(my_reqs.json()) >= 1
    req_id = my_reqs.json()[0]["id"]
    assert my_reqs.json()[0]["status"] == "PENDING"

    # Alice sees incoming request for her document
    incoming = client.get("/api/documents/incoming-requests", headers=user_headers)
    assert incoming.status_code == 200
    assert any(r["id"] == req_id for r in incoming.json())

    # Alice approves Bob's request
    action_res = client.post(
        f"/api/documents/requests/{req_id}/action",
        json={"status": "APPROVED", "actor_email": "alice@trustvault.com"},
        headers=user_headers
    )
    assert action_res.status_code == 200

    # Bob can now preview the document
    preview_res = client.get(f"/api/documents/{doc_id}/preview", headers=bob_headers)
    assert preview_res.status_code == 200

    # Alice revokes Bob's access
    revoke_res = client.post(
        f"/api/documents/requests/{req_id}/action",
        json={"status": "REVOKED", "actor_email": "alice@trustvault.com"},
        headers=user_headers
    )
    assert revoke_res.status_code == 200

    # Bob can no longer preview the document
    preview_denied = client.get(f"/api/documents/{doc_id}/preview", headers=bob_headers)
    assert preview_denied.status_code == 403
