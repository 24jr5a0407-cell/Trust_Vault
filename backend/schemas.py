from pydantic import BaseModel, EmailStr

class AccessRequestCreate(BaseModel):
    email: EmailStr

class AdminActionRequest(BaseModel):
    email: EmailStr
    status: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    secure_code: str
    full_name: str = None
    phone: str = None
    gender: str = None

class UserProfileUpdate(BaseModel):
    full_name: str = None
    phone: str = None
    gender: str = None
    profile_photo: str = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    otp: str = None

class SendLoginOtp(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordWithOtp(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

class GrantAccessRequest(BaseModel):
    user_email: EmailStr

class DocumentUpdate(BaseModel):
    filename: str

class RequestActionPayload(BaseModel):
    status: str  # APPROVED, REJECTED, REVOKED
    actor_email: str
    can_view: bool = True
    can_download: bool = False
    can_edit: bool = False

# Alias to prevent any AttributeError across routers
class RequestActionUpdate(BaseModel):
    status: str
    actor_email: str
    can_view: bool = True
    can_download: bool = False
    can_edit: bool = False
