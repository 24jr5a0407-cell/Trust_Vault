import os
from pathlib import Path
from dotenv import load_dotenv

# Locate and load .env file from project root or backend directory
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# Application & Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Turso Cloud Database
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "").strip()
LOCAL_DB_FILE = os.getenv("LOCAL_DB_FILE", "trust_vault.db")

# Backblaze B2 Storage
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME", "").strip()
B2_KEY_ID = os.getenv("B2_KEY_ID", "").strip()
B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY", "").strip()
B2_ENDPOINT_URL = os.getenv("B2_ENDPOINT_URL", "https://s3.us-east-005.backblazeb2.com").strip()

# Local upload directory fallback
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploaded_docs")

# JWT & Security
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-insecure-secret-key-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# File Upload Validation Constraints
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Default Admin Credentials
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "guardfile@gmail.com")
ADMIN_DEFAULT_PASSWORD = os.getenv("ADMIN_DEFAULT_PASSWORD", "Arshad@1234")
ADMIN_MASTER_CODE = os.getenv("ADMIN_MASTER_CODE", "ADMIN-MASTER-KEY")

# SMTP Email Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER).strip()
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Trust Vault Security").strip()
