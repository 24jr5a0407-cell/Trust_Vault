from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
import secrets
import csv
import io
import schemas
from database import get_db
from security import get_current_admin
from logger import logger
from email_service import send_email

router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])


@router.get("/requests")
def get_all_requests(
    current_admin: dict = Depends(get_current_admin),
    db = Depends(get_db)
):
    """Retrieves all pending and processed access requests for admin review with company employee status."""
    logger.info(f"Admin '{current_admin['email']}' viewing all whitelist access requests.")
    cursor = db.cursor()
    # Left join to check if the user belongs to company_employees active roster
    cursor.execute("""
        SELECT 
            au.id, 
            au.email, 
            au.status, 
            au.secure_code, 
            au.created_at,
            ce.full_name AS company_employee_name,
            ce.department AS company_department,
            CASE WHEN ce.id IS NOT NULL THEN 1 ELSE 0 END AS is_company_employee
        FROM allowed_users au
        LEFT JOIN company_employees ce ON LOWER(au.email) = LOWER(ce.email)
        ORDER BY au.id DESC
    """)
    rows = cursor.fetchall()
    results = []
    for row in rows:
        r = dict(row)
        # Security: Do not expose raw secure registration codes in the table for regular whitelist rows
        if r["email"] != "guardfilespace@gmail.com" and r["secure_code"] != "ADMIN-MASTER-KEY":
            r["secure_code_masked"] = "Sent to User's Email" if r["status"] == "APPROVED" else "N/A"
        else:
            r["secure_code_masked"] = "ADMIN-MASTER-KEY"
        results.append(r)
    return results


@router.post("/approve")
def approve_or_reject_user(
    action: schemas.AdminActionRequest,
    current_admin: dict = Depends(get_current_admin),
    db = Depends(get_db)
):
    """Admin approves or rejects a user access request and dispatches registration email."""
    logger.info(f"Admin '{current_admin['email']}' updating status for '{action.email}' to '{action.status}'")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM allowed_users WHERE email = ?", (action.email,))
    allowed_user = cursor.fetchone()
    
    status_val = action.status.upper()
    secure_code = None
    
    if status_val == "APPROVED":
        secure_code = f"TV-{secrets.token_hex(3).upper()}"
        logger.info(f"Generated secure registration code for '{action.email}': {secure_code}")
        
        # Dispatch Security Code directly to the user's registered email
        subject = "Trust Vault - Your Whitelist Access Request Has Been Approved!"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 520px; margin: auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #22c55e; margin-bottom: 8px;">🎉 Access Request Approved</h2>
            <p>Hello,</p>
            <p>Your access request to the <strong>Trust Vault</strong> system has been approved by the administrator.</p>
            <p>Here is your confidential <strong>Secure Registration Code</strong>:</p>
            <div style="font-size: 26px; font-weight: bold; letter-spacing: 3px; color: #4f46e5; background: #eef2ff; padding: 14px; text-align: center; border-radius: 6px; margin: 16px 0;">
                {secure_code}
            </div>
            <p>To complete your registration:</p>
            <ol style="color: #334155; line-height: 1.6;">
                <li>Visit the Trust Vault login page</li>
                <li>Switch to the <strong>Register</strong> tab</li>
                <li>Enter your approved email (<code>{action.email}</code>) and this security code</li>
                <li>Set your private password and sign in!</li>
            </ol>
            <p style="color: #64748b; font-size: 13px;">Security Note: Do not share this code with anyone. It can only be used once.</p>
        </div>
        """
        send_email(action.email, subject, html, f"Your Trust Vault Secure Code is: {secure_code}. Use this to register your account.")
        
    elif status_val == "REJECTED":
        logger.info(f"Access request for '{action.email}' was rejected.")
        subject = "Trust Vault - Access Whitelist Request Update"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #ef4444; margin-bottom: 8px;">Access Request Notice</h2>
            <p>Your access request for <strong>{action.email}</strong> was reviewed by the administrator and could not be approved at this time.</p>
            <p style="color: #64748b; font-size: 13px;">If you believe this is an error, please reach out directly to your organization administrator.</p>
        </div>
        """
        send_email(action.email, subject, html, "Your Trust Vault access request was not approved at this time.")

    if not allowed_user:
        cursor.execute("INSERT INTO allowed_users (email, status, secure_code) VALUES (?, ?, ?)", (action.email, status_val, secure_code))
    else:
        cursor.execute("UPDATE allowed_users SET status = ?, secure_code = ? WHERE email = ?", (status_val, secure_code, action.email))
    
    db.commit()
    return {"message": f"User {action.email} status updated to {status_val} and notified via email.", "secure_code": secure_code}


@router.post("/employees/import")
async def import_company_employees(
    file: UploadFile = File(...),
    current_admin: dict = Depends(get_current_admin),
    db = Depends(get_db)
):
    """
    Imports active company employees roster from a CSV or TXT file.
    Accepts CSV format with columns: email, name/full_name (optional), department (optional)
    or simple text file with one email per line.
    """
    logger.info(f"Admin '{current_admin['email']}' importing company active users file '{file.filename}'")
    filename = (file.filename or "").lower()
    if not (filename.endswith('.csv') or filename.endswith('.txt')):
        raise HTTPException(status_code=400, detail="Only CSV or TXT files are accepted for employee roster import.")

    content_bytes = await file.read()
    if len(content_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum roster size is 5MB.")

    try:
        text = content_bytes.decode('utf-8', errors='replace')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode file text: {str(e)}")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    cursor = db.cursor()
    imported_count = 0
    updated_count = 0

    if filename.endswith('.csv'):
        reader = csv.reader(lines)
        first_row = next(reader, None)
        if not first_row:
            raise HTTPException(status_code=400, detail="CSV file contains no data.")

        # Check if first row is a header
        header_lower = [col.strip().lower() for col in first_row]
        email_col = 0
        name_col = -1
        dept_col = -1

        if "email" in header_lower:
            email_col = header_lower.index("email")
            if "name" in header_lower:
                name_col = header_lower.index("name")
            elif "full_name" in header_lower:
                name_col = header_lower.index("full_name")
            if "department" in header_lower:
                dept_col = header_lower.index("department")
            rows_to_process = list(reader)
        else:
            # First row is data
            rows_to_process = [first_row] + list(reader)

        for row in rows_to_process:
            if not row or len(row) <= email_col:
                continue
            email_val = row[email_col].strip().lower()
            if not email_val or "@" not in email_val:
                continue

            name_val = row[name_col].strip() if name_col != -1 and len(row) > name_col else ""
            dept_val = row[dept_col].strip() if dept_col != -1 and len(row) > dept_col else "General"

            cursor.execute("SELECT id FROM company_employees WHERE LOWER(email) = ?", (email_val,))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("""
                    UPDATE company_employees 
                    SET full_name = COALESCE(NULLIF(?, ''), full_name),
                        department = COALESCE(NULLIF(?, ''), department)
                    WHERE id = ?
                """, (name_val, dept_val, existing["id"]))
                updated_count += 1
            else:
                cursor.execute("""
                    INSERT INTO company_employees (email, full_name, department)
                    VALUES (?, ?, ?)
                """, (email_val, name_val, dept_val))
                imported_count += 1
    else:
        # Plain text: one email per line
        for line in lines:
            parts = [p.strip() for p in line.split(",") if p.strip()]
            email_val = parts[0].lower() if parts else ""
            if not email_val or "@" not in email_val:
                continue
            name_val = parts[1] if len(parts) > 1 else ""
            dept_val = parts[2] if len(parts) > 2 else "General"

            cursor.execute("SELECT id FROM company_employees WHERE LOWER(email) = ?", (email_val,))
            existing = cursor.fetchone()
            if existing:
                updated_count += 1
            else:
                cursor.execute("""
                    INSERT INTO company_employees (email, full_name, department)
                    VALUES (?, ?, ?)
                """, (email_val, name_val, dept_val))
                imported_count += 1

    db.commit()
    logger.info(f"Imported {imported_count} new employees, updated {updated_count} existing records.")
    return {
        "message": f"Successfully processed company roster: {imported_count} imported, {updated_count} updated.",
        "imported": imported_count,
        "updated": updated_count
    }


@router.get("/employees")
def get_company_employees(
    current_admin: dict = Depends(get_current_admin),
    db = Depends(get_db)
):
    """Retrieves list of all pre-registered company employees."""
    cursor = db.cursor()
    cursor.execute("SELECT id, email, full_name, department, imported_at FROM company_employees ORDER BY id DESC")
    return [dict(row) for row in cursor.fetchall()]


@router.delete("/employees/{email}")
def remove_company_employee(
    email: str,
    current_admin: dict = Depends(get_current_admin),
    db = Depends(get_db)
):
    """Removes an employee from the company active roster."""
    cursor = db.cursor()
    cursor.execute("DELETE FROM company_employees WHERE LOWER(email) = LOWER(?)", (email,))
    db.commit()
    return {"message": f"Employee {email} removed from company roster."}


@router.get("/users")
def get_all_users(
    current_admin: dict = Depends(get_current_admin),
    db = Depends(get_db)
):
    """Admin retrieves all registered user accounts."""
    logger.info(f"Admin '{current_admin['email']}' listing all registered users.")
    cursor = db.cursor()
    cursor.execute("SELECT id, email, is_admin, created_at FROM users ORDER BY id ASC")
    return [dict(row) for row in cursor.fetchall()]


@router.delete("/users/{email}")
def remove_user(
    email: str,
    current_admin: dict = Depends(get_current_admin),
    db = Depends(get_db)
):
    """Admin removes a user account and reassigns documents to primary admin."""
    logger.info(f"Admin '{current_admin['email']}' requested deletion of user '{email}'")
    cursor = db.cursor()
    
    # Check if target is primary admin
    cursor.execute("SELECT is_admin FROM users WHERE email = ?", (email,))
    target = cursor.fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
        
    if email == current_admin["email"] or email == "guardfilespace@gmail.com":
        logger.warning(f"Attempted deletion of primary administrator account '{email}' blocked.")
        raise HTTPException(status_code=400, detail="Cannot remove primary admin account.")
        
    cursor.execute("UPDATE documents SET owner_email = ? WHERE owner_email = ?", (current_admin["email"], email))
    cursor.execute("DELETE FROM document_access WHERE user_email = ?", (email,))
    cursor.execute("DELETE FROM users WHERE email = ?", (email,))
    cursor.execute("DELETE FROM allowed_users WHERE email = ?", (email,))
    db.commit()
    logger.info(f"User '{email}' successfully removed by admin '{current_admin['email']}'")
    return {"message": f"User {email} removed successfully."}


@router.get("/documents")
def admin_get_all_documents(
    search: str = None,
    current_admin: dict = Depends(get_current_admin),
    db = Depends(get_db)
):
    """Admin views all official documents in the system with file-manager style search."""
    logger.info(f"Admin '{current_admin['email']}' fetching all documents (search={search}).")
    cursor = db.cursor()
    query = "SELECT * FROM documents WHERE is_personal = 0"
    params = []
    if search:
        term = search.strip()
        if term:
            if term.isdigit():
                query += " AND (id = ? OR LOWER(filename) LIKE LOWER(?) OR LOWER(owner_email) LIKE LOWER(?))"
                params.extend([int(term), f"%{term}%", f"%{term}%"])
            else:
                query += " AND (LOWER(filename) LIKE LOWER(?) OR LOWER(owner_email) LIKE LOWER(?))"
                params.extend([f"%{term}%", f"%{term}%"])
    query += " ORDER BY id DESC"
    cursor.execute(query, tuple(params))
    return [dict(row) for row in cursor.fetchall()]


@router.get("/ledger")
def admin_get_filtered_ledger(
    user_email: str = None,
    action: str = None,
    current_admin: dict = Depends(get_current_admin),
    db = Depends(get_db)
):
    """Admin views filtered immutable audit ledger."""
    logger.info(f"Admin '{current_admin['email']}' filtering ledger (user={user_email}, action={action})")
    cursor = db.cursor()
    query = """
        SELECT dl.id, dl.document_id, dl.user_email, dl.action, dl.timestamp, d.filename 
        FROM document_logs dl
        JOIN documents d ON dl.document_id = d.id
        WHERE 1=1
    """
    params = []
    if user_email:
        query += " AND dl.user_email LIKE ?"
        params.append(f"%{user_email}%")
    if action:
        query += " AND dl.action = ?"
        params.append(action)
        
    query += " ORDER BY dl.timestamp DESC"
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


@router.get("/ledger/export")
def export_ledger_csv(
    current_admin: dict = Depends(get_current_admin),
    db = Depends(get_db)
):
    """Admin exports immutable audit ledger as CSV."""
    logger.info(f"Admin '{current_admin['email']}' exporting audit ledger as CSV.")
    cursor = db.cursor()
    cursor.execute("""
        SELECT dl.id, dl.document_id, d.filename, dl.user_email, dl.action, dl.timestamp 
        FROM document_logs dl
        JOIN documents d ON dl.document_id = d.id
        ORDER BY dl.timestamp DESC
    """)
    logs = cursor.fetchall()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Log ID", "Document ID", "Filename", "User Email", "Action", "Timestamp"])
    for l in logs:
        writer.writerow([l["id"], l["document_id"], l["filename"], l["user_email"], l["action"], l["timestamp"]])
        
    response = Response(output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=audit_ledger_export.csv"
    return response
