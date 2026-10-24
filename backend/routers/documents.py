import os
import uuid
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse, StreamingResponse
import schemas
from database import get_db, UPLOAD_DIR
from b2_storage import upload_file_to_b2, get_file_from_b2, delete_file_from_b2
from security import get_current_user
from logger import logger
from file_validator import validate_file_upload

router = APIRouter(prefix="/api/documents", tags=["Document Management"])


@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    owner_email: str = Form(None),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Uploads an official document. Authenticated user becomes the owner."""
    effective_owner = current_user["email"] if current_user else owner_email
    
    # Production-level file security & content validation
    clean_filename, file_content = validate_file_upload(file)
    
    logger.info(f"Uploading official document '{clean_filename}' by owner '{effective_owner}'")
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM users WHERE email = ?", (effective_owner,))
    user = cursor.fetchone()
    if not user:
        logger.warning(f"Upload failed: Owner email '{effective_owner}' not found.")
        raise HTTPException(status_code=404, detail="Owner email not found in users table.")
    
    unique_filename = f"{uuid.uuid4()}_{clean_filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    memory_buffer = io.BytesIO(file_content)
    
    # Safely attempt local write for development/fallback if permitted
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
    except Exception as fs_err:
        logger.warning(f"Local disk write bypassed (serverless or read-only environment): {fs_err}")
        file_path = f"cloud://{unique_filename}"

    # Direct cloud upload to Backblaze B2
    try:
        memory_buffer.seek(0)
        upload_file_to_b2(memory_buffer, unique_filename, is_personal=False)
    except Exception as b2_err:
        logger.error(f"Backblaze B2 sync warning: {b2_err}")
        
    cursor.execute(
        "INSERT INTO documents (filename, stored_filename, file_path, owner_email) VALUES (?, ?, ?, ?)",
        (clean_filename, unique_filename, file_path, effective_owner)
    )
    document_id = cursor.lastrowid
    
    # Grant access to owner
    cursor.execute(
        "INSERT INTO document_access (document_id, user_email) VALUES (?, ?)",
        (document_id, effective_owner)
    )
    
    # Log upload action into audit ledger
    cursor.execute(
        "INSERT INTO document_logs (document_id, user_email, action) VALUES (?, ?, ?)",
        (document_id, effective_owner, "UPLOADED")
    )
    
    db.commit()
    logger.info(f"Official document '{clean_filename}' uploaded successfully with ID {document_id}")
    return {
        "message": "Document uploaded successfully!",
        "document_id": document_id,
        "filename": clean_filename,
        "owner": effective_owner
    }


@router.get("/")
def get_user_documents(
    user_email: str = None,
    search: str = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Fetch all official documents accessible by the authenticated user with optional search by ID or name."""
    effective_email = current_user["email"] if current_user else user_email
    logger.info(f"Fetching accessible documents for user: {effective_email} (search={search})")
    cursor = db.cursor()
    query = """
        SELECT DISTINCT d.id, d.filename, d.owner_email, d.created_at 
        FROM documents d
        LEFT JOIN document_access da ON d.id = da.document_id
        WHERE d.is_personal = 0 AND (d.owner_email = ? OR da.user_email = ?)
    """
    params = [effective_email, effective_email]
    
    if search:
        term = search.strip()
        if term:
            if term.isdigit():
                query += " AND (d.id = ? OR LOWER(d.filename) LIKE LOWER(?) OR LOWER(d.owner_email) LIKE LOWER(?))"
                params.extend([int(term), f"%{term}%", f"%{term}%"])
            else:
                query += " AND (LOWER(d.filename) LIKE LOWER(?) OR LOWER(d.owner_email) LIKE LOWER(?))"
                params.extend([f"%{term}%", f"%{term}%"])
                
    query += " ORDER BY d.id DESC"
    cursor.execute(query, tuple(params))
    return [dict(row) for row in cursor.fetchall()]


@router.get("/{document_id}/preview")
def preview_document(
    document_id: int,
    user_email: str = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """In-browser preview for admin, owner, or shared users with granted read access."""
    effective_email = current_user["email"] if current_user else user_email
    is_admin = bool(current_user.get("is_admin", False))
    logger.info(f"User '{effective_email}' requesting preview for document ID: {document_id}")
    
    cursor = db.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        logger.warning(f"Preview failed: Document ID {document_id} not found.")
        raise HTTPException(status_code=404, detail="Document not found.")
        
    if not is_admin:
        cursor.execute("SELECT is_admin FROM users WHERE email = ?", (effective_email,))
        user_row = cursor.fetchone()
        is_admin = bool(user_row["is_admin"]) if user_row else False
    
    cursor.execute("""
        SELECT * FROM documents d
        LEFT JOIN document_access da ON d.id = da.document_id
        WHERE d.id = ? AND (d.owner_email = ? OR da.user_email = ?)
    """, (document_id, effective_email, effective_email))
    has_access = cursor.fetchone() is not None
    
    if not is_admin and not has_access:
        logger.warning(f"Access denied for preview on document {document_id} to {effective_email}")
        raise HTTPException(status_code=403, detail="Access denied.")
        
    # Log view action in immutable audit ledger
    cursor.execute(
        "INSERT INTO document_logs (document_id, user_email, action) VALUES (?, ?, ?)",
        (document_id, effective_email, "VIEWED")
    )
    db.commit()
    
    # 1. Try local storage if file actually exists on disk
    if os.path.exists(doc["file_path"]):
        return FileResponse(path=doc["file_path"], filename=doc["filename"], content_disposition_type="inline")
    
    # 2. Direct streaming from Backblaze B2 cloud storage
    try:
        is_personal = bool(dict(doc).get("is_personal", 0))
        b2_key = f"personal-documents/{doc['owner_email'].replace('/', '_').strip()}/{doc['stored_filename']}" if is_personal else f"official-documents/{doc['stored_filename']}"
        stream, content_type = get_file_from_b2(b2_key)
        return StreamingResponse(stream, media_type=content_type, headers={"Content-Disposition": f"inline; filename=\"{doc['filename']}\""})
    except Exception as e:
        logger.error(f"Error streaming preview from cloud storage for doc {document_id}: {e}")
        raise HTTPException(status_code=404, detail="File missing from storage.")


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    user_email: str = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Download document. RESTRICTED: Only Owner or Admin can download."""
    effective_email = current_user["email"] if current_user else user_email
    is_admin = bool(current_user.get("is_admin", False))
    logger.info(f"Download requested for doc {document_id} by '{effective_email}'")
    
    cursor = db.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    if not is_admin:
        cursor.execute("SELECT is_admin FROM users WHERE email = ?", (effective_email,))
        user_row = cursor.fetchone()
        is_admin = bool(user_row["is_admin"]) if user_row else False
        
    is_owner = (doc["owner_email"] == effective_email)
    
    if not is_admin and not is_owner:
        logger.warning(f"Download forbidden: User '{effective_email}' is neither owner nor admin of doc {document_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Download restricted. You have read-only permissions and cannot download this file."
        )
        
    # Log download action
    cursor.execute(
        "INSERT INTO document_logs (document_id, user_email, action) VALUES (?, ?, ?)",
        (document_id, effective_email, "DOWNLOADED")
    )
    db.commit()
    
    # 1. Try local storage
    if os.path.exists(doc["file_path"]):
        return FileResponse(path=doc["file_path"], filename=doc["filename"], media_type="application/octet-stream")
        
    # 2. Cloud Backblaze B2 storage fallback
    try:
        is_personal = bool(dict(doc).get("is_personal", 0))
        b2_key = f"personal-documents/{doc['owner_email'].replace('/', '_').strip()}/{doc['stored_filename']}" if is_personal else f"official-documents/{doc['stored_filename']}"
        stream, content_type = get_file_from_b2(b2_key)
        return StreamingResponse(stream, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename=\"{doc['filename']}\""})
    except Exception as e:
        logger.error(f"Error streaming download from cloud storage for doc {document_id}: {e}")
        raise HTTPException(status_code=404, detail="Physical file missing from server.")


@router.put("/{document_id}")
def edit_document(
    document_id: int, 
    payload: schemas.DocumentUpdate, 
    user_email: str = None, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Edit document name/metadata. Only Owner or Admin can edit."""
    effective_email = current_user["email"] if current_user else user_email
    is_admin = bool(current_user.get("is_admin", False))
    logger.info(f"User '{effective_email}' editing document ID {document_id} to '{payload.filename}'")
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    if not is_admin:
        cursor.execute("SELECT is_admin FROM users WHERE email = ?", (effective_email,))
        user_row = cursor.fetchone()
        is_admin = bool(user_row["is_admin"]) if user_row else False
        
    is_owner = (doc["owner_email"] == effective_email)
    
    if not is_admin and not is_owner:
        logger.warning(f"Edit permission denied for user '{effective_email}' on doc {document_id}")
        raise HTTPException(status_code=403, detail="Permission denied. Only the owner or admin can edit this document.")
        
    cursor.execute("UPDATE documents SET filename = ? WHERE id = ?", (payload.filename, document_id))
    cursor.execute("INSERT INTO document_logs (document_id, user_email, action) VALUES (?, ?, ?)", (document_id, effective_email, f"RENAMED_TO_{payload.filename}"))
    db.commit()
    logger.info(f"Document {document_id} renamed successfully to '{payload.filename}'")
    return {"message": "Document updated successfully.", "new_filename": payload.filename}


@router.delete("/{document_id}")
def delete_document(
    document_id: int, 
    user_email: str = None, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """STRICT RULE: Only Administrators can delete official documents."""
    effective_email = current_user["email"] if current_user else user_email
    is_admin = bool(current_user.get("is_admin", False))
    logger.info(f"User '{effective_email}' requesting deletion of document ID {document_id}")
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    if not is_admin:
        cursor.execute("SELECT is_admin FROM users WHERE email = ?", (effective_email,))
        user_row = cursor.fetchone()
        is_admin = bool(user_row["is_admin"]) if user_row else False
        
    if not is_admin:
        logger.warning(f"Delete forbidden: User '{effective_email}' is not an admin.")
        raise HTTPException(status_code=403, detail="Permission denied. Only administrators can delete official documents.")
        
    # Log deletion in audit ledger before removing the record
    cursor.execute("INSERT INTO document_logs (document_id, user_email, action) VALUES (?, ?, ?)", (document_id, effective_email, "DELETED"))
    
    if os.path.exists(doc["file_path"]):
        try:
            os.remove(doc["file_path"])
        except Exception:
            pass

    # Delete from Backblaze B2 cloud storage
    try:
        is_personal = bool(dict(doc).get("is_personal", 0))
        b2_key = f"personal-documents/{doc['owner_email'].replace('/', '_').strip()}/{doc['stored_filename']}" if is_personal else f"official-documents/{doc['stored_filename']}"
        delete_file_from_b2(b2_key)
    except Exception as b2_err:
        logger.warning(f"B2 deletion warning: {b2_err}")
            
    cursor.execute("DELETE FROM document_logs WHERE document_id = ?", (document_id,))
    cursor.execute("DELETE FROM document_requests WHERE document_id = ?", (document_id,))
    cursor.execute("DELETE FROM document_access WHERE document_id = ?", (document_id,))
    cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    db.commit()
    logger.info(f"Official document {document_id} deleted successfully by admin '{effective_email}'")
    return {"message": "Document deleted successfully by admin and logged in audit ledger."}


@router.post("/{document_id}/grant")
def grant_document_access(
    document_id: int, 
    payload: schemas.GrantAccessRequest, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Owner or Admin grants read-only access to another approved user."""
    logger.info(f"User '{current_user['email']}' granting access on doc {document_id} to '{payload.user_email}'")
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    is_admin = bool(current_user.get("is_admin", False))
    is_owner = (doc["owner_email"] == current_user["email"])
    if not is_admin and not is_owner:
        raise HTTPException(status_code=403, detail="Permission denied. Only owner or admin can grant access.")
        
    cursor.execute("SELECT * FROM allowed_users WHERE email = ? AND status = 'APPROVED'", (payload.user_email,))
    if not cursor.fetchone():
        raise HTTPException(status_code=400, detail="User email is not approved in the whitelist.")
        
    cursor.execute("SELECT * FROM document_access WHERE document_id = ? AND user_email = ?", (document_id, payload.user_email))
    if cursor.fetchone():
        return {"message": f"User {payload.user_email} already has access."}
        
    cursor.execute("INSERT INTO document_access (document_id, user_email) VALUES (?, ?)", (document_id, payload.user_email))
    cursor.execute("INSERT INTO document_logs (document_id, user_email, action) VALUES (?, ?, ?)", (document_id, current_user["email"], f"GRANTED_ACCESS_TO_{payload.user_email}"))
    db.commit()
    logger.info(f"Access on doc {document_id} granted to '{payload.user_email}'")
    return {"message": f"Read-only access granted to {payload.user_email} successfully."}


@router.get("/{document_id}/ledger")
def get_document_ledger(
    document_id: int, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """View audit history for a specific document."""
    cursor = db.cursor()
    cursor.execute("SELECT id, user_email, action, timestamp FROM document_logs WHERE document_id = ? ORDER BY id DESC", (document_id,))
    return [dict(row) for row in cursor.fetchall()]


@router.get("/catalog")
def get_document_catalog(
    user_email: str = None, 
    search: str = None, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Searchable catalog of all documents in the system with file-manager style search (ID, full name, half-name, owner)."""
    effective_email = current_user["email"] if current_user else user_email
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
    docs = cursor.fetchall()
    
    catalog_results = []
    for doc in docs:
        doc_dict = dict(doc)
        is_owner = (doc_dict["owner_email"] == effective_email)
        
        cursor.execute("SELECT * FROM document_access WHERE document_id = ? AND user_email = ?", (doc_dict["id"], effective_email))
        has_access = cursor.fetchone() is not None
        
        cursor.execute("SELECT status FROM document_requests WHERE document_id = ? AND user_email = ? ORDER BY id DESC LIMIT 1", (doc_dict["id"], effective_email))
        req_row = cursor.fetchone()
        req_status = req_row["status"] if req_row else "NONE"
        
        doc_dict["is_owner"] = is_owner
        doc_dict["has_access"] = has_access or is_owner
        doc_dict["request_status"] = req_status
        catalog_results.append(doc_dict)
        
    return catalog_results


@router.post("/{document_id}/request-access")
def request_document_access(
    document_id: int, 
    user_email: str = None, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """User requests access to a document. Visible to owner and admin."""
    effective_email = current_user["email"] if current_user else user_email
    logger.info(f"User '{effective_email}' requesting access to doc ID {document_id}")
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    if doc["owner_email"] == effective_email:
        raise HTTPException(status_code=400, detail="You are already the owner of this document.")
        
    cursor.execute("SELECT * FROM document_requests WHERE document_id = ? AND user_email = ? AND status IN ('PENDING', 'APPROVED')", (document_id, effective_email))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="An active or pending request already exists for this document.")
        
    cursor.execute("INSERT INTO document_requests (document_id, user_email, status) VALUES (?, ?, 'PENDING')", (document_id, effective_email))
    cursor.execute("INSERT INTO document_logs (document_id, user_email, action) VALUES (?, ?, ?)", (document_id, effective_email, "REQUESTED_ACCESS"))
    db.commit()
    logger.info(f"Access request recorded for user '{effective_email}' on doc {document_id}")
    return {"message": "Access request submitted to document owner and admin successfully."}


@router.get("/my-requests")
def get_user_requests(
    user_email: str = None, 
    status: str = None, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """User views all their requested files with basic filter options."""
    effective_email = current_user["email"] if current_user else user_email
    cursor = db.cursor()
    query = """
        SELECT r.id, r.document_id, d.filename, d.owner_email, r.status, r.created_at
        FROM document_requests r
        JOIN documents d ON r.document_id = d.id
        WHERE r.user_email = ?
    """
    params = [effective_email]
    if status and status != "ALL":
        query += " AND r.status = ?"
        params.append(status)
        
    query += " ORDER BY r.created_at DESC"
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


@router.get("/incoming-requests")
def get_incoming_requests(
    email: str = None, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Owner or Admin views requests pending for documents they own or manage."""
    effective_email = current_user["email"] if current_user else email
    is_admin = bool(current_user.get("is_admin", False))
    cursor = db.cursor()
    
    if not is_admin:
        cursor.execute("SELECT is_admin FROM users WHERE email = ?", (effective_email,))
        user_row = cursor.fetchone()
        is_admin = bool(user_row["is_admin"]) if user_row else False
    
    if is_admin:
        cursor.execute("""
            SELECT r.id, r.document_id, d.filename, r.user_email, d.owner_email, r.status, r.created_at
            FROM document_requests r
            JOIN documents d ON r.document_id = d.id
            ORDER BY r.created_at DESC
        """)
    else:
        cursor.execute("""
            SELECT r.id, r.document_id, d.filename, r.user_email, d.owner_email, r.status, r.created_at
            FROM document_requests r
            JOIN documents d ON r.document_id = d.id
            WHERE d.owner_email = ?
            ORDER BY r.created_at DESC
        """, (effective_email,))
        
    return [dict(row) for row in cursor.fetchall()]


@router.post("/requests/{request_id}/action")
def handle_request_action(
    request_id: int, 
    payload: schemas.RequestActionPayload, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Owner or Admin approves, rejects, or revokes a request."""
    actor_email = current_user["email"] if current_user else payload.actor_email
    is_admin = bool(current_user.get("is_admin", False))
    logger.info(f"Handling request action for request ID {request_id} by actor '{actor_email}' -> {payload.status}")
    
    cursor = db.cursor()
    cursor.execute("SELECT r.*, d.owner_email FROM document_requests r JOIN documents d ON r.document_id = d.id WHERE r.id = ?", (request_id,))
    req = cursor.fetchone()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
        
    if not is_admin:
        cursor.execute("SELECT is_admin FROM users WHERE email = ?", (actor_email,))
        user_row = cursor.fetchone()
        is_admin = bool(user_row["is_admin"]) if user_row else False
        
    is_owner = (req["owner_email"] == actor_email)
    
    if not is_admin and not is_owner:
        logger.warning(f"Actor '{actor_email}' unauthorized to manage request {request_id}")
        raise HTTPException(status_code=403, detail="Permission denied. Only owner or admin can manage requests.")
        
    new_status = payload.status.upper()
    cursor.execute("UPDATE document_requests SET status = ? WHERE id = ?", (new_status, request_id))
    
    if new_status == "APPROVED":
        cursor.execute("SELECT * FROM document_access WHERE document_id = ? AND user_email = ?", (req["document_id"], req["user_email"]))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO document_access (document_id, user_email) VALUES (?, ?)", (req["document_id"], req["user_email"]))
        cursor.execute("INSERT INTO document_logs (document_id, user_email, action) VALUES (?, ?, ?)", (req["document_id"], actor_email, f"APPROVED_ACCESS_FOR_{req['user_email']}"))
    elif new_status in ["REJECTED", "REVOKED"]:
        cursor.execute("DELETE FROM document_access WHERE document_id = ? AND user_email = ?", (req["document_id"], req["user_email"]))
        cursor.execute("INSERT INTO document_logs (document_id, user_email, action) VALUES (?, ?, ?)", (req["document_id"], actor_email, f"{new_status}_ACCESS_FOR_{req['user_email']}"))
        
    db.commit()
    logger.info(f"Request {request_id} updated to status '{new_status}' successfully.")
    return {"message": f"Request status updated to {new_status} successfully."}


@router.post("/personal/upload")
def upload_personal_document(
    file: UploadFile = File(...),
    user_email: str = Form(None),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Uploads a strictly private personal document."""
    effective_user = current_user["email"] if current_user else user_email

    # Production-level file security & content validation
    clean_filename, file_content = validate_file_upload(file)

    logger.info(f"Uploading personal private document '{clean_filename}' for user: {effective_user}")
    cursor = db.cursor()
    unique_filename = f"{uuid.uuid4()}_{clean_filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    memory_buffer = io.BytesIO(file_content)
    
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
    except Exception as fs_err:
        logger.warning(f"Local disk write bypassed for personal doc: {fs_err}")
        file_path = f"cloud://{unique_filename}"

    # Direct Backblaze B2 upload in user-scoped personal subfolder
    try:
        memory_buffer.seek(0)
        upload_file_to_b2(memory_buffer, unique_filename, is_personal=True, user_email=effective_user)
    except Exception as b2_err:
        logger.error(f"Personal doc B2 cloud upload warning: {b2_err}")
        
    cursor.execute(
        "INSERT INTO documents (filename, stored_filename, file_path, owner_email, is_personal) VALUES (?, ?, ?, ?, 1)",
        (clean_filename, unique_filename, file_path, effective_user)
    )
    document_id = cursor.lastrowid
    
    cursor.execute(
        "INSERT INTO document_logs (document_id, user_email, action) VALUES (?, ?, ?)",
        (document_id, effective_user, "UPLOADED_PERSONAL_DOC")
    )
    db.commit()
    logger.info(f"Personal document {document_id} ('{clean_filename}') uploaded privately.")
    return {"message": "Personal document uploaded privately.", "document_id": document_id}


@router.get("/personal")
def get_personal_documents(
    user_email: str = None, 
    search: str = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieves personal documents belonging exclusively to the authenticated user with optional search."""
    effective_user = current_user["email"] if current_user else user_email
    cursor = db.cursor()
    query = "SELECT id, filename, created_at FROM documents WHERE owner_email = ? AND is_personal = 1"
    params = [effective_user]
    
    if search:
        term = search.strip()
        if term:
            if term.isdigit():
                query += " AND (id = ? OR LOWER(filename) LIKE LOWER(?))"
                params.extend([int(term), f"%{term}%"])
            else:
                query += " AND (LOWER(filename) LIKE LOWER(?))"
                params.extend([f"%{term}%"])
                
    query += " ORDER BY id DESC"
    cursor.execute(query, tuple(params))
    return [dict(row) for row in cursor.fetchall()]


@router.delete("/personal/{document_id}")
def delete_personal_document(
    document_id: int, 
    user_email: str = None, 
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Allows user to delete their own personal document without admin rights."""
    effective_user = current_user["email"] if current_user else user_email
    logger.info(f"User '{effective_user}' requested deletion of personal doc ID {document_id}")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ? AND owner_email = ? AND is_personal = 1", (document_id, effective_user))
    doc = cursor.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Personal document not found or unauthorized.")
        
    cursor.execute(
        "INSERT INTO document_logs (document_id, user_email, action) VALUES (?, ?, ?)",
        (document_id, effective_user, "DELETED_PERSONAL_DOC")
    )
    
    if os.path.exists(doc["file_path"]):
        try:
            os.remove(doc["file_path"])
        except Exception:
            pass

    try:
        is_personal = bool(dict(doc).get("is_personal", 0))
        b2_key = f"personal-documents/{doc['owner_email'].replace('/', '_').strip()}/{doc['stored_filename']}" if is_personal else f"official-documents/{doc['stored_filename']}"
        delete_file_from_b2(b2_key)
    except Exception as b2_err:
        logger.warning(f"B2 personal doc deletion warning: {b2_err}")
            
    cursor.execute("DELETE FROM document_logs WHERE document_id = ?", (document_id,))
    cursor.execute("DELETE FROM document_requests WHERE document_id = ?", (document_id,))
    cursor.execute("DELETE FROM document_access WHERE document_id = ?", (document_id,))
    cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    db.commit()
    logger.info(f"Personal document {document_id} deleted successfully.")
    return {"message": f"Personal document (ID: {document_id}) deleted successfully."}
