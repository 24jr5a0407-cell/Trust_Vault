import os
import sqlite3
import bcrypt
import libsql_client
from config import (
    TURSO_DATABASE_URL,
    TURSO_AUTH_TOKEN,
    LOCAL_DB_FILE,
    UPLOAD_DIR,
    ADMIN_EMAIL,
    ADMIN_DEFAULT_PASSWORD,
    ADMIN_MASTER_CODE
)
from logger import logger

# Backward compatibility alias
TURSO_URL = TURSO_DATABASE_URL

# Ensure local fallback upload directory exists if filesystem permits
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except Exception as e:
    logger.warning(f"Could not create local upload directory {UPLOAD_DIR}: {e}")

class TursoRow(dict):
    """Dictionary-like row that supports both dict indexing (row['email']) and tuple indexing (row[0])"""
    def __init__(self, columns, values):
        super().__init__(zip(columns, values))
        self._values = list(values)

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._values[item]
        return super().__getitem__(item)


class TursoCursor:
    def __init__(self, client):
        self.client = client
        self._last_result = None
        self._cursor_idx = 0
        self.lastrowid = None

    def execute(self, sql, params=None):
        args = list(params) if params is not None else []
        self._last_result = self.client.execute(sql, args)
        self._cursor_idx = 0
        self.lastrowid = getattr(self._last_result, 'last_insert_rowid', None)
        return self

    def fetchone(self):
        if not self._last_result or not self._last_result.rows:
            return None
        if self._cursor_idx >= len(self._last_result.rows):
            return None
        values = self._last_result.rows[self._cursor_idx]
        self._cursor_idx += 1
        cols = self._last_result.columns
        return TursoRow(cols, values)

    def fetchall(self):
        if not self._last_result or not self._last_result.rows:
            return []
        cols = self._last_result.columns
        rows = [TursoRow(cols, v) for v in self._last_result.rows[self._cursor_idx:]]
        self._cursor_idx = len(self._last_result.rows)
        return rows


class TursoConnection:
    def __init__(self, client):
        self.client = client

    def cursor(self):
        return TursoCursor(self.client)

    def commit(self):
        pass

    def close(self):
        try:
            self.client.close()
        except Exception:
            pass


def get_db():
    """Dependency for FastAPI routes. Connects directly to live Turso cloud database or local fallback."""
    conn = None
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        try:
            client = libsql_client.create_client_sync(url=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
            conn = TursoConnection(client)
        except Exception as e:
            logger.error(f"Error connecting to Turso cloud database: {e}. Falling back to SQLite.")
            conn = None

    if conn is None:
        conn = sqlite3.connect(LOCAL_DB_FILE, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.close()


def init_db(override_conn=None):
    """Initializes schema tables, indexes, and seeds the master administrator."""
    logger.info("Initializing database schema and indexes...")
    
    if override_conn is not None:
        conn = override_conn
        should_close = False
    elif TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        try:
            client = libsql_client.create_client_sync(url=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
            conn = TursoConnection(client)
            should_close = True
        except Exception as e:
            logger.error(f"Failed to connect to Turso in init_db: {e}. Using local SQLite.")
            conn = sqlite3.connect(LOCAL_DB_FILE, check_same_thread=False)
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.row_factory = sqlite3.Row
            should_close = True
    else:
        conn = sqlite3.connect(LOCAL_DB_FILE, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        should_close = True

    cursor = conn.cursor()

    # 1. Allowed Users Table (Whitelist)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'PENDING',
            secure_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Registered Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            full_name TEXT,
            phone TEXT,
            gender TEXT,
            profile_photo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Ensure profile columns exist in existing deployments
    for col_def in [
        ("full_name", "TEXT"),
        ("phone", "TEXT"),
        ("gender", "TEXT"),
        ("profile_photo", "TEXT")
    ]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_def[0]} {col_def[1]};")
        except Exception:
            pass

    # 3. Documents Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            owner_email TEXT NOT NULL,
            is_personal INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 4. Document Access Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_access (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            user_email TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
        );
    """)

    # 5. Document Ledger Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            user_email TEXT NOT NULL,
            action TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
        );
    """)

    # 6. Document Access Requests Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            user_email TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
        );
    """)

    # 7. OTP Verifications Table (Supports 5-minute expiry for Login 2FA and Forgot Password)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS otps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            otp TEXT NOT NULL,
            purpose TEXT NOT NULL, -- 'LOGIN' or 'RESET_PASSWORD'
            expires_at INTEGER NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 8. Company Active Roster (Pre-approved / Known Company Employees)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT,
            department TEXT,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Database Performance Indexes
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);",
        "CREATE INDEX IF NOT EXISTS idx_allowed_users_email ON allowed_users (email);",
        "CREATE INDEX IF NOT EXISTS idx_documents_owner ON documents (owner_email);",
        "CREATE INDEX IF NOT EXISTS idx_doc_access_user ON document_access (document_id, user_email);",
        "CREATE INDEX IF NOT EXISTS idx_doc_requests_lookup ON document_requests (document_id, user_email);",
        "CREATE INDEX IF NOT EXISTS idx_doc_logs_lookup ON document_logs (document_id, user_email);",
        "CREATE INDEX IF NOT EXISTS idx_company_emp_email ON company_employees (email);"
    ]
    for idx_sql in indexes:
        try:
            cursor.execute(idx_sql)
        except Exception as idx_err:
            logger.debug(f"Index creation note: {idx_err}")

    # Seed Default Master Administrator if not present
    cursor.execute("SELECT id, email, is_admin FROM users WHERE is_admin = 1;")
    admin_exists = cursor.fetchone()

    if not admin_exists:
        logger.info(f"Seeding master administrator account ({ADMIN_EMAIL})...")
        salt = bcrypt.gensalt()
        hashed_bytes = bcrypt.hashpw(ADMIN_DEFAULT_PASSWORD.encode('utf-8'), salt)
        hashed_password = hashed_bytes.decode('utf-8')

        cursor.execute(
            "INSERT OR IGNORE INTO users (email, hashed_password, is_admin) VALUES (?, ?, 1);",
            (ADMIN_EMAIL, hashed_password)
        )
        cursor.execute(
            "INSERT OR IGNORE INTO allowed_users (email, status, secure_code) VALUES (?, 'APPROVED', ?);",
            (ADMIN_EMAIL, ADMIN_MASTER_CODE)
        )
        conn.commit()
    else:
        logger.info("Master administrator account already exists.")

    if should_close:
        conn.close()
    logger.info("Database initialization completed successfully.")
