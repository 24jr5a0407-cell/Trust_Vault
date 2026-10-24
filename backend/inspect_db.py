import sqlite3

# Connect to your database
conn = sqlite3.connect("trust_vault.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("\n" + "="*40)
print(" 1. ALLOWED USERS (WHITELIST & REQUESTS) ")
print("="*40)
cursor.execute("SELECT * FROM allowed_users")
for row in cursor.fetchall():
    print(dict(row))

print("\n" + "="*40)
print(" 2. REGISTERED USERS (CREDENTIALS) ")
print("="*40)
cursor.execute("SELECT id, email, is_admin, created_at FROM users")
for row in cursor.fetchall():
    print(dict(row))

conn.close()
print("\n")