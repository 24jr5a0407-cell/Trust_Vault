import time
import random
from fastapi import APIRouter, Depends, HTTPException, status
import schemas
from database import get_db
from security import hash_password, verify_password, create_access_token
from logger import logger
from email_service import send_email

router = APIRouter(prefix="/api", tags=["User Authentication"])

OTP_VALIDITY_SECONDS = 300  # 5 minutes


def generate_otp() -> str:
    """Generates a secure 6-digit OTP."""
    return f"{random.randint(100000, 999999)}"


@router.post("/request-access")
def request_access(request: schemas.AccessRequestCreate, db = Depends(get_db)):
    """User submits email to request entry into the whitelist."""
    logger.info(f"Incoming access whitelist request for email: {request.email}")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM allowed_users WHERE email = ?", (request.email,))
    existing = cursor.fetchone()
    
    if existing:
        logger.info(f"Access request for {request.email} already exists with status: {existing['status']}")
        return {"message": f"Access request for {request.email} is already {existing['status']}."}
    
    cursor.execute("INSERT INTO allowed_users (email, status) VALUES (?, 'PENDING')", (request.email,))
    db.commit()
    logger.info(f"Access request submitted and set to PENDING for: {request.email}")
    return {"message": "Access request submitted successfully. Please wait for admin approval."}


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
    cursor.execute("INSERT INTO users (email, hashed_password, is_admin) VALUES (?, ?, 0)", (user_data.email, hashed_pwd))
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
    
    if not user or not verify_password(payload.password, user['hashed_password']):
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
    
    if not user or not verify_password(credentials.password, user['hashed_password']):
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
    
    logger.info(f"Password reset successfully completed for user: {payload.email}")
    return {"message": "Password changed successfully! You can now sign in with your new password."}
