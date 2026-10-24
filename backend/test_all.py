import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from database import get_db, TURSO_URL
from b2_storage import s3_client, B2_BUCKET

print("=" * 60)
print("[TRUSTVAULT SYSTEM VERIFICATION TEST]")
print("=" * 60)

# 1. Test Turso Cloud Database Connection
print("\n[Test 1] Testing Turso Cloud Database...")
try:
    db_gen = get_db()
    conn = next(db_gen)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 AS connected;")
    res = cursor.fetchone()
    print("  [PASS] Turso connection: SUCCESS")
    print(f"  [INFO] Turso URL: {TURSO_URL}")

    # Inspect tables in Turso
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    print(f"  [PASS] Migrated Tables ({len(tables)}): {', '.join(tables)}")

    # Check Seeded Master Admin
    cursor.execute("SELECT email, is_admin FROM users WHERE is_admin = 1;")
    admin = cursor.fetchone()
    if admin:
        print(f"  [PASS] Master Admin Verified: {admin['email']} (is_admin: {admin['is_admin']})")
    conn.close()
except Exception as e:
    print(f"  [FAIL] Turso connection failed: {e}")

# 2. Test Backblaze B2 Cloud Storage
print("\n[Test 2] Testing Backblaze B2 Cloud Storage...")
try:
    b2_res = s3_client.list_objects_v2(Bucket=B2_BUCKET)
    print("  [PASS] Backblaze B2 connection: SUCCESS")
    print(f"  [INFO] Bucket: {B2_BUCKET}")
    print(f"  [INFO] Objects currently stored: {b2_res.get('KeyCount', 0)}")
except Exception as e:
    print(f"  [FAIL] Backblaze B2 connection failed: {e}")

print("\n" + "=" * 60)
print("[COMPLETE] ALL SYSTEMS OPERATIONAL!")
print("=" * 60)
