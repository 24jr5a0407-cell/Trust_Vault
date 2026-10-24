from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
import secrets
import csv
import io
import schemas
from database import get_db
from security import get_current_admin
from logger import logger

router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])


@router.get("/requests")
def get_all_requests(
    current_admin: dict = Depends(get_current_admin),
    db = Depends(get_db)
):
    """Retrieves all pending and processed access requests for admin review."""
    logger.info(f"Admin '{current_admin['email']}' viewing all whitelist access requests.")
    cursor = db.cursor()
    cursor.execute("SELECT id, email, status, secure_code, created_at FROM allowed_users ORDER BY id DESC")
    return [dict(row) for row in cursor.fetchall()]


@router.post("/approve")
def approve_or_reject_user(
    action: schemas.AdminActionRequest,
    current_admin: dict = Depends(get_current_admin),
    db = Depends(get_db)
):
    """Admin approves or rejects a user access request."""
    logger.info(f"Admin '{current_admin['email']}' updating status for '{action.email}' to '{action.status}'")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM allowed_users WHERE email = ?", (action.email,))
    allowed_user = cursor.fetchone()
    
    status_val = action.status.upper()
    secure_code = None
    
    if status_val == "APPROVED":
        secure_code = f"TV-{secrets.token_hex(3).upper()}"
        logger.info(f"Generated secure registration code for '{action.email}': {secure_code}")
    elif status_val == "REJECTED":
        logger.info(f"Access request for '{action.email}' was rejected.")

    if not allowed_user:
        cursor.execute("INSERT INTO allowed_users (email, status, secure_code) VALUES (?, ?, ?)", (action.email, status_val, secure_code))
    else:
        cursor.execute("UPDATE allowed_users SET status = ?, secure_code = ? WHERE email = ?", (status_val, secure_code, action.email))
    
    db.commit()
    return {"message": f"User {action.email} status updated to {status_val}.", "secure_code": secure_code}


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
        
    if email == current_admin["email"] or email == "guardfile@gmail.com":
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
