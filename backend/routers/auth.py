import time
import random
from fastapi import APIRouter, Depends, HTTPException, status
import schemas
from database import get_db
from security import hash_password, verify_password, create_access_token
from logger import logger
from email_service import send_email
from config import ADMIN_EMAIL

router = APIRouter(prefix="/api", tags=["User Authentication"])

OTP_VALIDITY_SECONDS = 300  # 5 minutes


def generate_otp() -> str:
    """Generates a secure 6-digit OTP."""
    return f"{random.randint(100000, 999999)}"


@router.post("/request-access")
def request_access(request: schemas.AccessRequestCreate, db = Depends(get_db)):
    """User submits email to request entry into the whitelist and notifies the administrator."""
    logger.info(f"Incoming access whitelist request for email: {request.email}")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM allowed_users WHERE email = ?", (request.email,))
    existing = cursor.fetchone()
    
    if existing:
        logger.info(f"Access request for {request.email} already exists with status: {existing['status']}")
        return {"message": f"Access request for {request.email} is already {existing['status']}."}
    
    cursor.execute(
        "INSERT INTO allowed_users (email, status, full_name, phone, department) VALUES (?, 'PENDING', ?, ?, ?)", 
        (request.email, request.full_name or '', request.phone or '', request.department or '')
    )
    db.commit()
    logger.info(f"Access request submitted and set to PENDING for: {request.email}")

    # Dispatch immediate email alert to system admin with candidate's entered credentials
    try:
        subject = f"[Trust Vault Whitelist Alert] New Access Request Submitted - {request.email}"
        details_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 550px; margin: auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 10px; background-color: #ffffff;">
            <h2 style="color: #0284c7; margin-bottom: 6px; font-size: 1.25rem;">👤 New User Awaiting Administrator Approval</h2>
            <p style="color: #475569; font-size: 0.95rem; margin-bottom: 16px;">A new user has submitted a registration request on Trust Vault and is waiting for authorization:</p>
            <div style="background: #f8fafc; border-left: 4px solid #0284c7; padding: 14px 18px; border-radius: 6px; margin: 16px 0;">
                <p style="margin: 4px 0;"><strong>User Email:</strong> <span style="color: #0f172a;">{request.email}</span></p>
                <p style="margin: 4px 0;"><strong>Full Name:</strong> <span style="color: #0f172a;">{request.full_name or 'Not specified'}</span></p>
                <p style="margin: 4px 0;"><strong>Phone Number:</strong> <span style="color: #0f172a;">{request.phone or 'Not specified'}</span></p>
                <p style="margin: 4px 0;"><strong>Department / Role:</strong> <span style="color: #0f172a;">{request.department or 'Not specified'}</span></p>
                <p style="margin: 4px 0;"><strong>Submission Status:</strong> <span style="color: #d97706; font-weight: bold;">PENDING REVIEW</span></p>
            </div>
            <p style="color: #64748b; font-size: 0.88rem; line-height: 1.5;">
                Please log in to your <a href="https://trust-vault.onrender.com/admin.html" style="color: #0284c7; font-weight: bold;">Admin Control Panel</a> to verify their company roster match and approve or revoke their access.
            </p>
        </div>
        """
        send_email(
            to_email=ADMIN_EMAIL,
            subject=subject,
            html_content=details_html,
            text_content=f"New access request awaiting approval: {request.email} (Name: {request.full_name}, Phone: {request.phone}, Department: {request.department})"
        )
        logger.info(f"Admin notification email dispatched successfully to {ADMIN_EMAIL} for {request.email}")
    except Exception as mail_err:
        logger.warning(f"Could not send admin notification email: {mail_err}")

    return {"message": "Access request submitted successfully. Administrator notified. Please wait for approval."}


@router.post("/register")
def register_user(user_data: schemas.UserRegister, db = Depends(get_db)):
    """Registers an approved user after validating their secure registration code."""
    logger.info(f"Registration attempt for email: {user_data.email}")
    cursor = db.cursor()
    
    # Check if email is approved and secure code matches
    cursor.execute("SELECT * FROM allowed_users WHERE email = ? AND status = 'APPROVED'", (user_data.email,))
    allowed = cursor.fetchone()
    
    if not allowed:
        logger.warning(f"Registration rejected: {user_data.email} is not approved in whitelist.")
        raise HTTPException(status_code=403, detail="Email not approved in whitelist.")
    
    if allowed['secure_code'] != user_data.secure_code:
        logger.warning(f"Registration rejected: Invalid secure code for {user_data.email}.")
        raise HTTPException(status_code=403, detail="Invalid secure registration code.")
    
    cursor.execute("SELECT * FROM users WHERE email = ?", (user_data.email,))
    if cursor.fetchone():
        logger.warning(f"Registration rejected: Account already exists for {user_data.email}.")
        raise HTTPException(status_code=400, detail="Account already exists. Please sign in.")
    
    hashed_pwd = hash_password(user_data.password)
    cursor.execute("""
        INSERT INTO users (email, hashed_password, is_admin, full_name, phone, gender) 
        VALUES (?, ?, 0, ?, ?, ?)
    """, (user_data.email, hashed_pwd, user_data.full_name or '', user_data.phone or '', user_data.gender or ''))
    db.commit()
    
    logger.info(f"User registration successful for: {user_data.email}")
    return {"message": "Account created successfully! You can now sign in."}


@router.post("/send-login-otp")
def send_login_otp(payload: schemas.SendLoginOtp, db = Depends(get_db)):
    """
    Validates user email & password first; if valid, generates and sends a 5-minute Login OTP.
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (payload.email,))
    user = cursor.fetchone()
    
    if not user:
        raise HTTPException(
            status_code=404, 
            detail="Account not found. Please submit an access request to the administrator and register your account."
        )
        
    if not verify_password(payload.password, user['hashed_password']):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
        
    otp = generate_otp()
    expires_at = int(time.time()) + OTP_VALIDITY_SECONDS
    
    # Invalidate previous unused login OTPs for this email
    cursor.execute("UPDATE otps SET used = 1 WHERE email = ? AND purpose = 'LOGIN' AND used = 0", (payload.email,))
    cursor.execute(
        "INSERT INTO otps (email, otp, purpose, expires_at, used) VALUES (?, ?, 'LOGIN', ?, 0)",
        (payload.email, otp, expires_at)
    )
    db.commit()
    
    # Send OTP Email
    subject = "Trust Vault - Your Login Verification Code (OTP)"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #4f46e5; margin-bottom: 8px;">🔒 Trust Vault Login Verification</h2>
        <p>You requested to sign in to your Trust Vault account (<strong>{payload.email}</strong>).</p>
        <p>Your one-time login verification code is:</p>
        <div style="font-size: 28px; font-weight: bold; letter-spacing: 4px; color: #1e293b; background: #f1f5f9; padding: 12px; text-align: center; border-radius: 6px; margin: 16px 0;">
            {otp}
        </div>
        <p style="color: #64748b; font-size: 13px;">This code is valid for <strong>5 minutes</strong>. If you did not attempt to log in, please secure your account immediately.</p>
    </div>
    """
    email_result = send_email(payload.email, subject, html, f"Your Trust Vault Login OTP is: {otp} (Valid for 5 minutes)")
    
    return {
        "message": f"Verification code (OTP) sent to your registered email ({payload.email})! Valid for 5 minutes.",
        "email": payload.email
    }


@router.post("/login")
def login_user(credentials: schemas.UserLogin, db = Depends(get_db)):
    """
    Authenticates email, password, and verified OTP.
    """
    logger.info(f"Authentication attempt for user: {credentials.email}")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (credentials.email,))
    user = cursor.fetchone()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Account not found. Please submit an access request to the administrator and register your account."
        )
    
    if not verify_password(credentials.password, user['hashed_password']):
        logger.warning(f"Failed login attempt for email: {credentials.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    
    # Check OTP verification
    if not credentials.otp:
        raise HTTPException(status_code=400, detail="OTP is required. Please request an OTP first.")
        
    now = int(time.time())
    cursor.execute(
        "SELECT * FROM otps WHERE email = ? AND purpose = 'LOGIN' AND used = 0 ORDER BY id DESC LIMIT 1",
        (credentials.email,)
    )
    otp_record = cursor.fetchone()
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="No active OTP found. Please request a new verification code.")
        
    if otp_record['expires_at'] < now:
        raise HTTPException(status_code=400, detail="OTP has expired (valid 5 minutes). Please request a new code.")
        
    if otp_record['otp'] != credentials.otp.strip():
        raise HTTPException(status_code=400, detail="Invalid OTP code.")
        
    # Mark OTP as used
    cursor.execute("UPDATE otps SET used = 1 WHERE id = ?", (otp_record['id'],))
    db.commit()
    
    is_admin = bool(user['is_admin'])
    token_payload = {
        "sub": user['email'],
        "email": user['email'],
        "is_admin": is_admin
    }
    access_token = create_access_token(token_payload)
    
    logger.info(f"Login successful for user: {credentials.email} (is_admin: {is_admin}). JWT issued.")
    return {
        "message": "Login successful!",
        "access_token": access_token,
        "token_type": "bearer",
        "email": user['email'],
        "is_admin": is_admin
    }


@router.post("/forgot-password")
def forgot_password(payload: schemas.ForgotPasswordRequest, db = Depends(get_db)):
    """
    Initiates password reset: Generates a 6-digit OTP valid for 5 minutes and emails it.
    """
    cursor = db.cursor()
    cursor.execute("SELECT id, email FROM users WHERE email = ?", (payload.email,))
    user = cursor.fetchone()
    if not user:
        # Avoid user enumeration attack, but return clean message
        return {"message": "If this email is registered in Trust Vault, a 5-minute reset OTP has been sent."}
        
    otp = generate_otp()
    expires_at = int(time.time()) + OTP_VALIDITY_SECONDS
    
    # Invalidate previous unused reset OTPs
    cursor.execute("UPDATE otps SET used = 1 WHERE email = ? AND purpose = 'RESET_PASSWORD' AND used = 0", (payload.email,))
    cursor.execute(
        "INSERT INTO otps (email, otp, purpose, expires_at, used) VALUES (?, ?, 'RESET_PASSWORD', ?, 0)",
        (payload.email, otp, expires_at)
    )
    db.commit()
    
    # Dispatch Email
    subject = "Trust Vault - Password Reset Code (OTP)"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #4f46e5; margin-bottom: 8px;">🔒 Trust Vault Password Reset</h2>
        <p>We received a request to reset the password for your Trust Vault account (<strong>{payload.email}</strong>).</p>
        <p>Your one-time password reset code is:</p>
        <div style="font-size: 28px; font-weight: bold; letter-spacing: 4px; color: #1e293b; background: #f1f5f9; padding: 12px; text-align: center; border-radius: 6px; margin: 16px 0;">
            {otp}
        </div>
        <p style="color: #64748b; font-size: 13px;">This code is valid for <strong>5 minutes</strong>. If you did not request this, please ignore this email.</p>
    </div>
    """
    send_email(payload.email, subject, html, f"Your Trust Vault Password Reset OTP is: {otp} (Valid for 5 minutes)")
    
    return {
        "message": f"Password reset OTP sent to your registered email ({payload.email})! Valid for 5 minutes.",
        "email": payload.email
    }


@router.post("/reset-password")
def reset_password(payload: schemas.ResetPasswordWithOtp, db = Depends(get_db)):
    """
    Verifies the 5-minute OTP and updates the user's password.
    """
    cursor = db.cursor()
    cursor.execute("SELECT id, email FROM users WHERE email = ?", (payload.email,))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")
        
    now = int(time.time())
    cursor.execute(
        "SELECT * FROM otps WHERE email = ? AND purpose = 'RESET_PASSWORD' AND used = 0 ORDER BY id DESC LIMIT 1",
        (payload.email,)
    )
    otp_record = cursor.fetchone()
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="No active password reset OTP found. Please request a new one.")
        
    if otp_record['expires_at'] < now:
        raise HTTPException(status_code=400, detail="Reset OTP has expired (valid 5 minutes). Please request a new code.")
        
    if otp_record['otp'] != payload.otp.strip():
        raise HTTPException(status_code=400, detail="Invalid OTP code.")
        
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters.")
        
    # Mark OTP as used and update password
    cursor.execute("UPDATE otps SET used = 1 WHERE id = ?", (otp_record['id'],))
    new_hashed = hash_password(payload.new_password)
    cursor.execute("UPDATE users SET hashed_password = ? WHERE email = ?", (new_hashed, payload.email))
    db.commit()
    logger.info(f"Password reset successful for: {payload.email}")
    return {"message": "Password reset successful! You can now sign in with your new password."}


@router.get("/profile")
def get_user_profile(user_email: str = None, db = Depends(get_db)):
    """Retrieves current user profile information."""
    if not user_email:
        raise HTTPException(status_code=400, detail="User email required.")
    cursor = db.cursor()
    cursor.execute("SELECT id, email, is_admin, full_name, phone, gender, profile_photo, created_at FROM users WHERE email = ?", (user_email,))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    data = dict(user)
    return data


@router.put("/profile")
def update_user_profile(payload: schemas.UserProfileUpdate, user_email: str = None, db = Depends(get_db)):
    """Updates user profile information (name, phone, gender, profile photo)."""
    if not user_email:
        raise HTTPException(status_code=400, detail="User email required.")
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (user_email,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="User not found.")
    
    cursor.execute("""
        UPDATE users 
        SET full_name = COALESCE(?, full_name),
            phone = COALESCE(?, phone),
            gender = COALESCE(?, gender),
            profile_photo = COALESCE(?, profile_photo)
        WHERE email = ?
    """, (payload.full_name, payload.phone, payload.gender, payload.profile_photo, user_email))
    db.commit()
    logger.info(f"User profile updated for '{user_email}'")
    return {"message": "Profile updated successfully!"}
    
    logger.info(f"Password reset successfully completed for user: {payload.email}")
    return {"message": "Password changed successfully! You can now sign in with your new password."}
