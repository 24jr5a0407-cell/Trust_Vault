import pytest
from config import ADMIN_EMAIL, ADMIN_DEFAULT_PASSWORD

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Trust Vault" in response.text or "status" in response.text

def test_health_check_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_admin_login_success(client, test_db):
    # 1. Send Login OTP
    otp_res = client.post("/api/send-login-otp", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_DEFAULT_PASSWORD
    })
    assert otp_res.status_code == 200
    assert "Verification code" in otp_res.json()["message"]

    # Retrieve generated OTP from test database
    cursor = test_db.cursor()
    cursor.execute("SELECT otp FROM otps WHERE email = ? AND purpose = 'LOGIN' ORDER BY id DESC LIMIT 1", (ADMIN_EMAIL,))
    row = cursor.fetchone()
    assert row is not None
    otp_code = row["otp"]

    # 2. Login with OTP
    response = client.post("/api/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_DEFAULT_PASSWORD,
        "otp": otp_code
    })
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Login successful!"
    assert data["is_admin"] is True
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_password(client):
    response = client.post("/api/login", json={
        "email": ADMIN_EMAIL,
        "password": "WrongPassword!",
        "otp": "123456"
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]

def test_access_request_and_registration_lifecycle(client, admin_headers, test_db):
    user_email = "newuser@example.com"
    
    # 1. Request access
    req_res = client.post("/api/request-access", json={"email": user_email})
    assert req_res.status_code == 200
    assert "submitted successfully" in req_res.json()["message"]
    
    # Duplicate access request returns existing status
    dup_res = client.post("/api/request-access", json={"email": user_email})
    assert dup_res.status_code == 200
    assert "already PENDING" in dup_res.json()["message"]

    # 2. Admin approves access request
    approve_res = client.post("/api/admin/approve", json={
        "email": user_email,
        "status": "APPROVED"
    }, headers=admin_headers)
    assert approve_res.status_code == 200
    secure_code = approve_res.json()["secure_code"]
    assert secure_code.startswith("TV-")

    # 3. Registration with invalid secure code fails
    fail_reg = client.post("/api/register", json={
        "email": user_email,
        "password": "UserSecurePassword123",
        "secure_code": "INVALID-CODE"
    })
    assert fail_reg.status_code == 403

    # 4. Registration with valid code succeeds
    success_reg = client.post("/api/register", json={
        "email": user_email,
        "password": "UserSecurePassword123",
        "secure_code": secure_code
    })
    assert success_reg.status_code == 200
    assert "Account created successfully" in success_reg.json()["message"]

    # 5. Send login OTP for new user
    user_otp_res = client.post("/api/send-login-otp", json={
        "email": user_email,
        "password": "UserSecurePassword123"
    })
    assert user_otp_res.status_code == 200
    cursor = test_db.cursor()
    cursor.execute("SELECT otp FROM otps WHERE email = ? AND purpose = 'LOGIN' ORDER BY id DESC LIMIT 1", (user_email,))
    user_otp = cursor.fetchone()["otp"]

    # 6. Login with newly created user and OTP
    login_res = client.post("/api/login", json={
        "email": user_email,
        "password": "UserSecurePassword123",
        "otp": user_otp
    })
    assert login_res.status_code == 200
    assert login_res.json()["is_admin"] is False
    assert "access_token" in login_res.json()
