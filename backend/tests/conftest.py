import os
import sys
import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import database
from main import app
from database import get_db, init_db
from security import create_access_token

# Test in-memory / temporary database
TEST_DB_PATH = backend_dir / "test_trustvault.db"

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(monkeypatch_session=None):
    """Initializes test environment and mocks cloud storage."""
    # Mock B2 storage operations to avoid external cloud network calls during unit testing
    import b2_storage
    b2_storage.upload_file_to_b2 = lambda file_obj, filename, is_personal=False, user_email="": f"mock/{filename}"
    b2_storage.delete_file_from_b2 = lambda storage_key: None


@pytest.fixture(scope="function")
def test_db():
    """Provides a fresh isolated test SQLite database for every test function."""
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

    conn = sqlite3.connect(str(TEST_DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row

    # Initialize tables and seed master admin
    init_db(override_conn=conn)

    def override_get_db():
        c = sqlite3.connect(str(TEST_DB_PATH), check_same_thread=False)
        c.execute("PRAGMA foreign_keys = ON;")
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_db] = override_get_db

    yield conn

    conn.close()
    app.dependency_overrides.clear()
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass


@pytest.fixture
def client(test_db):
    """FastAPI TestClient with isolated test database."""
    return TestClient(app)


@pytest.fixture
def admin_headers():
    """Authorization header with valid Admin JWT token."""
    token = create_access_token({"sub": "admin@trustvault.com", "email": "admin@trustvault.com", "is_admin": True})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers():
    """Authorization header with standard User JWT token."""
    token = create_access_token({"sub": "alice@trustvault.com", "email": "alice@trustvault.com", "is_admin": False})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def bob_headers():
    """Authorization header for another standard user."""
    token = create_access_token({"sub": "bob@trustvault.com", "email": "bob@trustvault.com", "is_admin": False})
    return {"Authorization": f"Bearer {token}"}
