from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
import secrets
import csv
import io
import openpyxl
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
            au.full_name AS submitted_full_name,
            au.phone AS submitted_phone,
            au.department AS submitted_department,
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
        # Strict Organization Validation: If active company employees roster is configured, enforce membership
        cursor.execute("SELECT COUNT(*) as count FROM company_employees")
        roster_count_row = cursor.fetchone()
        roster_count = roster_count_row["count"] if isinstance(roster_count_row, dict) else (roster_count_row[0] if roster_count_row else 0)

        is_root_admin = action.email.lower() == "guardfilespace@gmail.com"
        
        if roster_count > 0 and not is_root_admin:
            cursor.execute("SELECT id, full_name, department FROM company_employees WHERE LOWER(email) = LOWER(?)", (action.email,))
            company_emp = cursor.fetchone()
            if not company_emp:
                logger.warning(f"Admin approval blocked: '{action.email}' is NOT in active company employees roster.")
                raise HTTPException(
                    status_code=400,
                    detail=f"Approval rejected: '{action.email}' does not belong to the imported Company Employees roster. Only verified company employees can be approved."
                )

        secure_code = f"TV-{secrets.token_hex(3).upper()}"
        logger.info(f"Generated secure registration code for verified company employee '{action.email}': {secure_code}")
        
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
    Imports active company employees roster from an Excel (.xlsx, .xls), CSV, or TXT file.
    Accepts spreadsheet / CSV with columns: Email, Name / Full Name, Department.
    """
    logger.info(f"Admin '{current_admin['email']}' importing company active users file '{file.filename}'")
    filename = (file.filename or "").lower()
    valid_exts = ('.xlsx', '.xls', '.csv', '.txt')
    if not any(filename.endswith(ext) for ext in valid_exts):
        raise HTTPException(
            status_code=400, 
            detail="Invalid file format. Please upload an Excel sheet (.xlsx, .xls), CSV (.csv), or TXT file."
        )

    content_bytes = await file.read()
    if len(content_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum roster size is 10MB.")

    extracted_records = []

    if filename.endswith('.xlsx') or filename.endswith('.xls'):
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content_bytes), data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                raise HTTPException(status_code=400, detail="The Excel sheet is empty.")

            first_row = [str(cell).strip().lower() if cell is not None else "" for cell in rows[0]]
            email_idx = -1
            name_idx = -1
            dept_idx = -1

            for i, h in enumerate(first_row):
                if "email" in h or "mail" in h:
                    email_idx = i
                elif "name" in h:
                    name_idx = i
                elif "department" in h or "dept" in h or "role" in h:
                    dept_idx = i

            data_rows = rows[1:] if email_idx != -1 else rows
            if email_idx == -1:
                # Default assume col 0 is Name or Email
                email_idx = 1 if len(first_row) > 1 and "@" in str(rows[0][1] or "") else 0
                name_idx = 0 if email_idx == 1 else (1 if len(first_row) > 1 else -1)

            for r in data_rows:
                if not r or len(r) <= email_idx or r[email_idx] is None:
                    continue
                email_str = str(r[email_idx]).strip().lower()
                if not email_str or "@" not in email_str or "." not in email_str:
                    continue
                name_str = str(r[name_idx]).strip() if name_idx != -1 and len(r) > name_idx and r[name_idx] is not None else ""
                dept_str = str(r[dept_idx]).strip() if dept_idx != -1 and len(r) > dept_idx and r[dept_idx] is not None else "General"
                extracted_records.append((email_str, name_str, dept_str))
        except HTTPException:
            raise
        except Exception as xl_err:
            logger.error(f"Excel parsing error: {xl_err}")
            raise HTTPException(status_code=400, detail=f"Failed to parse Excel sheet: {str(xl_err)}")

    elif filename.endswith('.csv'):
        try:
            text = content_bytes.decode('utf-8', errors='replace')
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            reader = csv.reader(lines)
            rows = list(reader)
            if not rows:
                raise HTTPException(status_code=400, detail="CSV file is empty.")

            header_lower = [col.strip().lower() for col in rows[0]]
            email_col = 0
            name_col = -1
            dept_col = -1

            if any("email" in h for h in header_lower):
                for i, h in enumerate(header_lower):
                    if "email" in h or "mail" in h:
                        email_col = i
                    elif "name" in h:
                        name_col = i
                    elif "department" in h or "dept" in h:
                        dept_col = i
                data_rows = rows[1:]
            else:
                data_rows = rows

            for r in data_rows:
                if not r or len(r) <= email_col:
                    continue
                email_str = r[email_col].strip().lower()
                if not email_str or "@" not in email_str:
                    continue
                name_str = r[name_col].strip() if name_col != -1 and len(r) > name_col else ""
                dept_str = r[dept_col].strip() if dept_col != -1 and len(r) > dept_col else "General"
                extracted_records.append((email_str, name_str, dept_str))
        except Exception as csv_err:
            raise HTTPException(status_code=400, detail=f"Failed to parse CSV file: {str(csv_err)}")
    else:
        # Plain text
        text = content_bytes.decode('utf-8', errors='replace')
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",") if p.strip()]
            email_str = parts[0].lower() if parts else ""
            if not email_str or "@" not in email_str:
                continue
            name_str = parts[1] if len(parts) > 1 else ""
            dept_str = parts[2] if len(parts) > 2 else "General"
            extracted_records.append((email_str, name_str, dept_str))

    if not extracted_records:
        raise HTTPException(
            status_code=400, 
            detail="No valid employee email records found in the uploaded file. Please ensure columns include Email."
        )

    cursor = db.cursor()
    imported_count = 0
    updated_count = 0

    for email_val, name_val, dept_val in extracted_records:
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

    db.commit()
    logger.info(f"Imported {imported_count} new employees, updated {updated_count} existing records.")
    return {
        "message": f"Successfully imported {imported_count} new employees ({updated_count} updated) into Company Roster!",
        "imported": imported_count,
        "updated": updated_count,
        "total_roster": imported_count + updated_count
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
    query = "SELECT id, filename, stored_filename, file_path, owner_email, is_personal, created_at, last_edited_by, last_edited_at FROM documents WHERE is_personal = 0"
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
