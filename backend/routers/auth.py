from fastapi import APIRouter, Depends, HTTPException, status
import schemas
from database import get_db
from security import hash_password, verify_password, create_access_token
from logger import logger

router = APIRouter(prefix="/api", tags=["User Authentication"])


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
    
    if allowed['secure_code'] != user_data.secure_code.strip():
        logger.warning(f"Registration rejected: Invalid secure registration code for {user_data.email}.")
        raise HTTPException(status_code=400, detail="Invalid secure registration code provided.")
    
    cursor.execute("SELECT * FROM users WHERE email = ?", (user_data.email,))
    if cursor.fetchone():
        logger.warning(f"Registration rejected: Account already exists for {user_data.email}.")
        raise HTTPException(status_code=400, detail="Account already exists. Please sign in.")
    
    hashed_pwd = hash_password(user_data.password)
    cursor.execute("INSERT INTO users (email, hashed_password, is_admin) VALUES (?, ?, 0)", (user_data.email, hashed_pwd))
    db.commit()
    
    logger.info(f"User registration successful for: {user_data.email}")
    return {"message": "Account created successfully! You can now sign in."}


@router.post("/login")
def login_user(credentials: schemas.UserLogin, db = Depends(get_db)):
    """Authenticates credentials and issues a secure JWT bearer token."""
    logger.info(f"Authentication attempt for user: {credentials.email}")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (credentials.email,))
    user = cursor.fetchone()
    
    if not user or not verify_password(credentials.password, user['hashed_password']):
        logger.warning(f"Failed login attempt for email: {credentials.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    
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
