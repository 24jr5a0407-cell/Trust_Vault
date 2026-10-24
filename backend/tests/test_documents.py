import io
import pytest

def register_user(client, admin_headers, email, password):
    client.post("/api/request-access", json={"email": email})
    approve_res = client.post("/api/admin/approve", json={"email": email, "status": "APPROVED"}, headers=admin_headers)
    code = approve_res.json()["secure_code"]
    client.post("/api/register", json={"email": email, "password": password, "secure_code": code})

def test_document_upload_and_catalog(client, admin_headers, user_headers):
    # Setup user
    register_user(client, admin_headers, "alice@trustvault.com", "Password123")
    
    # Alice uploads an official document
    file_bytes = b"Hello, this is confidential corporate content."
    res = client.post(
        "/api/documents/upload",
        files={"file": ("report.txt", io.BytesIO(file_bytes), "text/plain")},
        headers=user_headers
    )
    assert res.status_code == 200
    doc_id = res.json()["document_id"]
    assert res.json()["filename"] == "report.txt"
    assert res.json()["owner"] == "alice@trustvault.com"

    # Alice queries user documents
    user_docs = client.get("/api/documents/", headers=user_headers)
    assert user_docs.status_code == 200
    assert any(d["id"] == doc_id for d in user_docs.json())

    # Check Catalog
    catalog = client.get("/api/documents/catalog", headers=user_headers)
    assert catalog.status_code == 200
    found = [d for d in catalog.json() if d["id"] == doc_id]
    assert len(found) == 1
    assert found[0]["is_owner"] is True

def test_document_preview_and_download_permissions(client, admin_headers, user_headers, bob_headers):
    register_user(client, admin_headers, "alice@trustvault.com", "Password123")
    register_user(client, admin_headers, "bob@trustvault.com", "Password123")

    # Alice uploads document
    file_bytes = b"Secret Specs"
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("specs.txt", io.BytesIO(file_bytes), "text/plain")},
        headers=user_headers
    )
    doc_id = upload_res.json()["document_id"]

    # Bob tries preview without permission -> 403 Forbidden
    bob_preview = client.get(f"/api/documents/{doc_id}/preview", headers=bob_headers)
    assert bob_preview.status_code == 403

    # Alice grants access to Bob
    grant_res = client.post(
        f"/api/documents/{doc_id}/grant",
        json={"user_email": "bob@trustvault.com"},
        headers=user_headers
    )
    assert grant_res.status_code == 200

    # Bob can now preview
    bob_preview_allowed = client.get(f"/api/documents/{doc_id}/preview", headers=bob_headers)
    assert bob_preview_allowed.status_code == 200

    # Bob tries to download -> 403 Forbidden (Download is restricted to Owner/Admin)
    bob_download = client.get(f"/api/documents/{doc_id}/download", headers=bob_headers)
    assert bob_download.status_code == 403

    # Alice (Owner) can download
    alice_download = client.get(f"/api/documents/{doc_id}/download", headers=user_headers)
    assert alice_download.status_code == 200

    # Admin can also download
    admin_download = client.get(f"/api/documents/{doc_id}/download", headers=admin_headers)
    assert admin_download.status_code == 200

def test_personal_documents_isolation(client, admin_headers, user_headers, bob_headers):
    register_user(client, admin_headers, "alice@trustvault.com", "Password123")
    register_user(client, admin_headers, "bob@trustvault.com", "Password123")

    # Alice uploads personal document
    res = client.post(
        "/api/documents/personal/upload",
        files={"file": ("private_tax.pdf", io.BytesIO(b"%PDF-1.4\nMy personal tax form"), "application/pdf")},
        headers=user_headers
    )
    assert res.status_code == 200
    doc_id = res.json()["document_id"]

    # Alice sees her personal document
    alice_personal = client.get("/api/documents/personal", headers=user_headers)
    assert alice_personal.status_code == 200
    assert any(d["id"] == doc_id for d in alice_personal.json())

    # Bob does NOT see Alice's personal document
    bob_personal = client.get("/api/documents/personal", headers=bob_headers)
    assert bob_personal.status_code == 200
    assert not any(d["id"] == doc_id for d in bob_personal.json())

    # Bob cannot delete Alice's personal document
    bob_del = client.delete(f"/api/documents/personal/{doc_id}", headers=bob_headers)
    assert bob_del.status_code == 404

    # Alice can delete her own personal document
    alice_del = client.delete(f"/api/documents/personal/{doc_id}", headers=user_headers)
    assert alice_del.status_code == 200

def test_file_manager_search_by_id_name_and_half_name(client, admin_headers, user_headers):
    register_user(client, admin_headers, "alice@trustvault.com", "Password123")

    # Upload multiple documents with distinct names
    client.post(
        "/api/documents/upload",
        files={"file": ("Financial_Quarterly_Report_2026.pdf", io.BytesIO(b"%PDF-1.4\nFinance 2026"), "application/pdf")},
        headers=user_headers
    )
    client.post(
        "/api/documents/upload",
        files={"file": ("System_Architecture_Blueprint.png", io.BytesIO(b"\x89PNG\r\n\x1a\n\x00Blueprint"), "image/png")},
        headers=user_headers
    )
    client.post(
        "/api/documents/upload",
        files={"file": ("Employee_Onboarding_Handbook.docx", io.BytesIO(b"PK\x03\x04\x00Onboarding"), "application/octet-stream")},
        headers=user_headers
    )

    # 1. Search by exact full name
    search_full = client.get("/api/documents/catalog?search=System_Architecture_Blueprint.png", headers=user_headers)
    assert search_full.status_code == 200
    assert len(search_full.json()) == 1
    assert "Architecture" in search_full.json()[0]["filename"]

    # 2. Search by half-name / partial substring (case-insensitive)
    search_half = client.get("/api/documents/catalog?search=quarter", headers=user_headers)
    assert search_half.status_code == 200
    assert len(search_half.json()) == 1
    assert "Financial_Quarterly_Report_2026.pdf" == search_half.json()[0]["filename"]

    # Another half-name search
    search_half2 = client.get("/api/documents/catalog?search=board", headers=user_headers)
    assert search_half2.status_code == 200
    assert len(search_half2.json()) == 1
    assert "Employee_Onboarding_Handbook.docx" == search_half2.json()[0]["filename"]

    # 3. Search by file ID
    target_id = search_half.json()[0]["id"]
    search_id = client.get(f"/api/documents/catalog?search={target_id}", headers=user_headers)
    assert search_id.status_code == 200
    assert any(d["id"] == target_id for d in search_id.json())

    # 4. Search in Accessible Documents (/api/documents/?search=...)
    vault_search = client.get("/api/documents/?search=Blueprint", headers=user_headers)
    assert vault_search.status_code == 200
    assert len(vault_search.json()) == 1
    assert "System_Architecture_Blueprint.png" == vault_search.json()[0]["filename"]

    # 5. Search in Admin Documents (/api/admin/documents?search=...)
    admin_search = client.get("/api/admin/documents?search=Report", headers=admin_headers)
    assert admin_search.status_code == 200
    assert any("Report" in d["filename"] for d in admin_search.json())

    # 6. Search by Owner Name / Email (Full or Half/Partial name)
    owner_search = client.get("/api/documents/catalog?search=alice", headers=user_headers)
    assert owner_search.status_code == 200
    assert len(owner_search.json()) >= 3
    assert all("alice" in d["owner_email"].lower() for d in owner_search.json())

