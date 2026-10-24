from fastapi import APIRouter, Depends, HTTPException, status
import schemas
from database import get_db
from security import get_current_user
from logger import logger
from email_service import send_email

router = APIRouter(prefix="/api/requests", tags=["User Document Requests"])


@router.get("/search")
def search_documents(
    query: str, 
    user_email: str = None, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Search documents by ID or filename and attach request status."""
    effective_user = current_user["email"] if current_user else user_email
    logger.info(f"User '{effective_user}' searching documents with query '{query}'")
    cursor = db.cursor()
    
    if query.isdigit():
        cursor.execute("""
            SELECT d.id, d.filename, d.owner_email, d.created_at 
            FROM documents d WHERE d.id = ? AND d.is_personal = 0
        """, (int(query),))
    else:
        cursor.execute("""
            SELECT d.id, d.filename, d.owner_email, d.created_at 
            FROM documents d WHERE d.filename LIKE ? AND d.is_personal = 0
        """, (f"%{query}%",))
        
    documents = [dict(row) for row in cursor.fetchall()]
    
    results = []
    for doc in documents:
        cursor.execute("""
            SELECT status FROM document_requests 
            WHERE document_id = ? AND user_email = ?
            ORDER BY id DESC LIMIT 1
        """, (doc["id"], effective_user))
        req = cursor.fetchone()
        doc_data = dict(doc)
        doc_data["request_status"] = req["status"] if req else "NOT_REQUESTED"
        results.append(doc_data)
        
    return results


@router.post("/{document_id}/request")
def request_document_access(
    document_id: int, 
    user_email: str = None, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Creates or resubmits a request visible to owner and admin."""
    effective_user = current_user["email"] if current_user else user_email
    logger.info(f"User '{effective_user}' requesting access to doc {document_id}")
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    if doc["owner_email"] == effective_user:
        raise HTTPException(status_code=400, detail="You are the owner of this document.")

    cursor.execute("""
        SELECT * FROM document_requests WHERE document_id = ? AND user_email = ?
    """, (document_id, effective_user))
    existing = cursor.fetchone()
    
    if existing:
        if existing["status"] == "APPROVED":
            return {"message": "Access is already approved.", "status": "APPROVED"}
        elif existing["status"] == "PENDING":
            return {"message": "Request is already pending review.", "status": "PENDING"}
        else:
            cursor.execute("""
                UPDATE document_requests SET status = 'PENDING' 
                WHERE document_id = ? AND user_email = ?
            """, (document_id, effective_user))
    else:
        cursor.execute("""
            INSERT INTO document_requests (document_id, user_email, status) 
            VALUES (?, ?, 'PENDING')
        """, (document_id, effective_user))
        
    db.commit()
    logger.info(f"Request set to PENDING for '{effective_user}' on doc {document_id}")
    
    # Send Notification Email to Document Owner
    try:
        subject = f"Trust Vault - Access Requested for Document: {doc['filename']}"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #4f46e5; margin-bottom: 8px;">📄 New Document Access Request</h2>
            <p>User <strong>{effective_user}</strong> has requested permission to access your document:</p>
            <div style="background: #f8fafc; padding: 12px; border-left: 4px solid #4f46e5; margin: 15px 0;">
                <p style="margin: 0; font-weight: bold;">{doc['filename']} (ID: #{doc['id']})</p>
            </div>
            <p>You can review and approve or reject this request anytime in your Trust Vault dashboard under <em>'Incoming Requests'</em>.</p>
        </div>
        """
        send_email(doc["owner_email"], subject, html, f"User {effective_user} requested access to {doc['filename']}.")
    except Exception as notify_err:
        logger.warning(f"Could not send owner notification email: {notify_err}")

    return {"message": "Access request sent successfully to document owner and admin.", "status": "PENDING"}


@router.get("/{document_id}/status")
def check_request_status(
    document_id: int, 
    user_email: str = None, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Check current status of the request."""
    effective_user = current_user["email"] if current_user else user_email
    cursor = db.cursor()
    cursor.execute("""
        SELECT status, created_at FROM document_requests 
        WHERE document_id = ? AND user_email = ?
        ORDER BY id DESC LIMIT 1
    """, (document_id, effective_user))
    req = cursor.fetchone()
    
    if not req:
        return {"status": "NOT_REQUESTED", "message": "No request made yet."}
        
    return {"status": req["status"], "created_at": req["created_at"]}


@router.get("/my-requests")
def get_user_requested_files(
    user_email: str = None, 
    status_filter: str = None, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """User views requested files with basic filter options."""
    effective_user = current_user["email"] if current_user else user_email
    cursor = db.cursor()
    
    query = """
        SELECT r.id as request_id, d.id as document_id, d.filename, d.owner_email, r.status, r.created_at
        FROM document_requests r
        JOIN documents d ON r.document_id = d.id
        WHERE r.user_email = ?
    """
    params = [effective_user]
    
    if status_filter:
        query += " AND r.status = ?"
        params.append(status_filter.upper())
        
    query += " ORDER BY r.created_at DESC"
    cursor.execute(query, tuple(params))
    return [dict(row) for row in cursor.fetchall()]


@router.post("/manage/{request_id}")
def handle_request_approval(
    request_id: int, 
    payload: schemas.RequestActionPayload, 
    reviewer_email: str = None, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Admin or Document Owner can approve/reject request."""
    effective_reviewer = current_user["email"] if current_user else (reviewer_email or payload.actor_email)
    is_admin = bool(current_user.get("is_admin", False))
    logger.info(f"Reviewer '{effective_reviewer}' managing request ID {request_id} -> {payload.status}")
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT r.*, d.owner_email FROM document_requests r
        JOIN documents d ON r.document_id = d.id
        WHERE r.id = ?
    """, (request_id,))
    req = cursor.fetchone()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
        
    if not is_admin:
        cursor.execute("SELECT is_admin FROM users WHERE email = ?", (effective_reviewer,))
        user_row = cursor.fetchone()
        is_admin = bool(user_row["is_admin"]) if user_row else False
        
    is_owner = (req["owner_email"] == effective_reviewer)
    
    if not is_admin and not is_owner:
        raise HTTPException(status_code=403, detail="Only the document owner or an admin can manage this request.")
        
    new_status = payload.status.upper()
    cursor.execute("UPDATE document_requests SET status = ? WHERE id = ?", (new_status, request_id))
    
    if new_status == "APPROVED":
        cursor.execute("SELECT * FROM document_access WHERE document_id = ? AND user_email = ?", (req["document_id"], req["user_email"]))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO document_access (document_id, user_email) VALUES (?, ?)", (req["document_id"], req["user_email"]))
    elif new_status in ["REJECTED", "REVOKED"]:
        cursor.execute("DELETE FROM document_access WHERE document_id = ? AND user_email = ?", (req["document_id"], req["user_email"]))
        
    db.commit()
    logger.info(f"Request {request_id} updated to {new_status} by {effective_reviewer}")
    
    # Notify requesting user via email of permission grant or rejection
    try:
        cursor.execute("SELECT filename FROM documents WHERE id = ?", (req["document_id"],))
        d_row = cursor.fetchone()
        fname = d_row["filename"] if d_row else f"Document #{req['document_id']}"
        
        status_color = "#22c55e" if new_status == "APPROVED" else "#ef4444"
        subject = f"Trust Vault - Document Access {new_status}: {fname}"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: {status_color}; margin-bottom: 8px;">Document Access {new_status}</h2>
            <p>Your access request for <strong>{fname}</strong> has been updated to <strong>{new_status}</strong> by {effective_reviewer}.</p>
            {f"<p>You can now view this document in your <strong>My Vault</strong> dashboard.</p>" if new_status == "APPROVED" else "<p>You do not currently have access to view this document.</p>"}
        </div>
        """
        send_email(req["user_email"], subject, html, f"Your request for {fname} was marked as {new_status}.")
    except Exception as notify_err:
        logger.warning(f"Could not send user permission update email: {notify_err}")

    return {"message": f"Request status updated to {new_status} successfully by {effective_reviewer}."}


@router.delete("/revoke/{document_id}/{target_email}")
def revoke_document_access(
    document_id: int, 
    target_email: str, 
    reviewer_email: str = None, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Owner or Admin revokes access."""
    effective_reviewer = current_user["email"] if current_user else reviewer_email
    is_admin = bool(current_user.get("is_admin", False))
    logger.info(f"Reviewer '{effective_reviewer}' revoking access on doc {document_id} for target '{target_email}'")
    cursor = db.cursor()
    
    cursor.execute("SELECT owner_email FROM documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    if not is_admin:
        cursor.execute("SELECT is_admin FROM users WHERE email = ?", (effective_reviewer,))
        user_row = cursor.fetchone()
        is_admin = bool(user_row["is_admin"]) if user_row else False
        
    is_owner = (doc["owner_email"] == effective_reviewer)
    
    if not is_admin and not is_owner:
        raise HTTPException(status_code=403, detail="Permission denied to revoke access.")
        
    cursor.execute("DELETE FROM document_access WHERE document_id = ? AND user_email = ?", (document_id, target_email))
    cursor.execute("""
        UPDATE document_requests SET status = 'REVOKED' 
        WHERE document_id = ? AND user_email = ?
    """, (document_id, target_email))
    
    db.commit()
    logger.info(f"Access revoked for {target_email} on doc {document_id}")
    
    # Send revocation notification email
    try:
        fname = doc["filename"] if doc else f"Document #{document_id}"
        subject = f"Trust Vault - Document Access Revoked: {fname}"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #ef4444; margin-bottom: 8px;">Access Revoked</h2>
            <p>Your access permissions to <strong>{fname}</strong> have been revoked by {effective_reviewer}.</p>
            <p style="color: #64748b; font-size: 13px;">You will need to submit a new request if you require access in the future.</p>
        </div>
        """
        send_email(target_email, subject, html, f"Your access to {fname} has been revoked.")
    except Exception as notify_err:
        logger.warning(f"Could not send revocation email: {notify_err}")

    return {"message": f"Access revoked for {target_email}. User must re-request to gain access again."}
