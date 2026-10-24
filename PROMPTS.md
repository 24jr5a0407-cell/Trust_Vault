# 📝 PROMPTS.md: Comprehensive Engineering Prompt Log & Decision Trace

> **Project**: Trust Vault — Enterprise Cloud Document Vault & Security System  
> **Repository**: [https://github.com/24jr5a0407-cell/Trust_Vault](https://github.com/24jr5a0407-cell/Trust_Vault)  
> **Author & Lead Developer**: `24jr5a0407-cell` (`24jr5a0407@gmail.com`)  
> **Purpose**: Detailed chronological and categorized log documenting the exact prompts used to build the entire Trust Vault system from scratch, analyzing the AI tool's initial output, the security/architectural flaws identified, the human engineer's corrective intervention, and references to commits.

---

## 📑 Prompt Taxonomy & Framework

Every major engineering milestone in this document is structured into three formal prompt engineering categories:
1. **System Prompt / Architectural Context**: The role, constraints, operating environment, and security invariants set for the AI assistant.
2. **Context & Requirement Prompts**: The state of the system, data models, compliance requirements, and specific user stories.
3. **Instruction Prompts (Direct Actions)**: The precise implementation directives issued to generate, refactor, or harden code.

---

## 🏛️ Phase 1: Project Genesis & Architecture Inception

### Prompt Entry 1.1: Foundations & Architecture Design
* **Date**: October 23, 2026
* **System Prompt / Role**:
  > "Act as a Senior Principal Cloud Architect and Application Security Specialist. You are mentoring a beginner engineer to build a high-security, enterprise-grade cloud document vault from scratch using Python (FastAPI), vanilla JavaScript, cloud database, and cloud object storage with zero server maintenance costs."
* **Context & Requirement Prompt**:
  > "I want to build the Trust Vault document protector application from scratch. I am very beginner to FastAPI and JavaScript and building web applications. Help me build the application such that I can store all the documents in the cloud and explain each and every thing in an interview. I want to use Python for the backend, suggest a simple UI and backend, and suggest how to store user details like passwords and files. I will do each task one by one starting from file structure to deployment."
* **Instruction Prompt**:
  > "1. Provide an enterprise-grade, clean directory structure separating backend, frontend, tests, and configuration.  
  > 2. Recommend the best serverless database and cloud object storage stack that costs $0 to run and will impress enterprise interviewers.  
  > 3. Provide the foundational `requirements.txt` with FastAPI, Uvicorn, bcrypt, PyJWT, and boto3."
* **What the Tool Produced**:
  - Suggested SQLite for local testing and recommended **Turso (distributed libSQL)** for cloud relational data and **Backblaze B2 (S3-compatible)** for document object storage.
  - Outlined the clean directory layout:
    ```
    Trust_Vault/
    ├── backend/
    │   ├── routers/ (auth, admin, documents, requests)
    │   ├── database.py, config.py, security.py, file_validator.py
    │   └── tests/
    ├── public/ (index.html, dashboard.html, admin.html, script.js, style.css)
    └── vercel.json
    ```
* **What was Wrong / Security Analysis**:
  - The tool initially suggested storing passwords using plain SHA-256 without salting.
* **Engineering Action & Fix**:
  - Intervened immediately: replaced SHA-256 with **bcrypt** salted hashing (`bcrypt.gensalt()`, `bcrypt.hashpw`) to prevent rainbow table attacks.
* **Commit Reference**: [`de97d5c`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/de97d5c806509fba24be7e382b60f5451ec3aa48)

---

## 🔐 Phase 2: Dual-Tier Onboarding & Admin Governance (Authorisation & Access Control)

### Prompt Entry 2.1: Admin Whitelist & User Registration Flow
* **Date**: October 23, 2026
* **System Prompt / Role**:
  > "You are a Security Systems Engineer implementing Zero-Trust network and application onboarding policies."
* **Context & Requirement Prompt**:
  > "I am thinking that first I will do the admin part where admin can do the following: I want to maintain active users of the application in a table so that only users in that table will be able to login, others will not. When a new user wants to login, they send a request to admin. The admin adds them to the active table, then the user can create a password and sign in. Maintain another table for username and password details so existing users can sign in without asking admin every time."
* **Instruction Prompt**:
  > "1. Create the `allowed_users` (whitelist) and `users` (credentials) tables in `database.py`.  
  > 2. Seed a default master administrator account on startup if none exists.  
  > 3. Create the `/api/request-access`, `/api/admin/approve`, and `/api/register` endpoints. Implement single-use registration codes (`TV-XXXXXX`) so users cannot register without approval."
* **What the Tool Produced**:
  - Created tables: `allowed_users (id, email, status, secure_code)` and `users (id, email, hashed_password, is_admin)`.
  - Created admin approval endpoints, but printed the raw `secure_code` in plaintext in the admin HTML table and allowed anyone with an approved email to register without verifying the secret token.
* **What was Wrong / Security Analysis**:
  - **Severe Access Control Vulnerability**: Without requiring the user to present the exact `secure_code`, any user who knew their request was marked "APPROVED" could register without proving they owned the address or received the admin's secret approval token.
* **Engineering Action & Fix**:
  - Hardened `/api/register` to strictly enforce:
    ```python
    if allowed['secure_code'] != user_data.secure_code:
        raise HTTPException(status_code=403, detail="Invalid secure registration code.")
    ```
  - Masked the security codes in the admin dashboard so only the approved recipient receives the code out-of-band via email.
* **Commit Reference**: [`5a278fb`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/5a278fbd078331c3739c38242ce7ef357683e766)

---

## 📁 Phase 3: Document Catalog, Ownership & Immutable Ledger (Audit Control)

### Prompt Entry 3.1: Document Ownership & Audit Ledger Architecture
* **Date**: October 23, 2026
* **System Prompt / Role**:
  > "Act as a Compliance and Data Governance Architect designing an immutable, non-repudiation audit trail."
* **Context & Requirement Prompt**:
  > "I want to create endpoints so admin and document owners can upload a new file, edit that file, and download it. Maintain the documents table with file name, id, creator, timestamp, and who has access. When a file is uploaded or opened, maintain a ledger of who opened the file and at what time. For every file, admin is default owner; in future if any user creates files, they are owner along with admin."
* **Instruction Prompt**:
  > "1. Implement `documents`, `document_access`, and `document_logs` tables in `database.py`.  
  > 2. Implement `/api/documents/upload`, `/api/documents/{id}/preview`, and `/api/admin/ledger`.  
  > 3. Log every view and upload action in `document_logs` with UTC timestamps. Ensure non-owners cannot download or view documents without explicit access grants."
* **What the Tool Produced**:
  - Generated document management tables and basic logging.
  - Implemented an endpoint `DELETE /api/admin/ledger/clear` so admins could "clear out old logs."
* **What was Wrong / Security Analysis**:
  - **Audit Repudiation Flaw**: A core tenet of ISO 27001 and SOC 2 compliance is that an audit ledger must be **append-only and immutable**. Giving any user or administrator an endpoint to delete or clear audit records allows malicious insiders to erase proof of unauthorized access.
* **Engineering Action & Fix**:
  - Completely stripped out all `DELETE` or `UPDATE` capabilities on `document_logs`.
  - Added an immutable CSV export route (`/api/admin/ledger/export`) so auditors can safely backup historical logs to external cold storage.
* **Commit Reference**: [`5a278fb`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/5a278fbd078331c3739c38242ce7ef357683e766)

---

### Prompt Entry 3.2: Granular Access Requests & User Removal Governance
* **Date**: October 24, 2026
* **System Prompt / Role**:
  > "Act as a Senior Identity & Access Management (IAM) Engineer."
* **Context & Requirement Prompt**:
  > "User requesting code owners for file access: only read-only access should be given, no download and no edit options. Admin can remove users; when admin removes a user, document ownership should revert to admin alone and the user should be removed from active users. Admin should have access to ledger logs, documents table, and all employee details except login passwords."
* **Instruction Prompt**:
  > "1. Create the `document_requests` workflow: user requests access -> owner or admin reviews -> status changes to APPROVED/REJECTED.  
  > 2. In `DELETE /api/admin/users/{email}`, clean up active access permissions and reassign any orphaned documents to the active administrator.  
  > 3. Block regular users from downloading files (`/api/documents/{id}/download`)."
* **What the Tool Produced**:
  - Implemented `document_requests` routing.
  - Allowed any admin to delete any user record, including the root master administrator account.
* **What was Wrong / Security Analysis**:
  - **Privilege Escalation / System Bricking**: If a secondary administrator or compromised session deleted `guardfilespace@gmail.com`, the organization would lose the primary administrative root key and lock itself out of platform configuration.
* **Engineering Action & Fix**:
  - Added an immutable check protecting the master administrator:
    ```python
    if email == current_admin["email"] or email == "guardfilespace@gmail.com":
        raise HTTPException(status_code=400, detail="Cannot remove primary admin account.")
    ```
  - Added unit test `test_cannot_delete_primary_admin` in `backend/tests/test_admin.py` to assert this boundary permanently.
* **Commit Reference**: [`ac9c98d`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/ac9c98d533dc4fa708791bcbe885a7c12fae1dd5)

---

## 🔒 Phase 4: Zero-Trust Private Personal Vault Isolation

### Prompt Entry 4.1: Personal Vault & Private Data Segregation
* **Date**: October 24, 2026
* **System Prompt / Role**:
  > "Act as a Cryptographic Privacy Architect implementing Zero-Knowledge and user data isolation."
* **Context & Requirement Prompt**:
  > "I want to create another tab in the dashboard so that anyone can upload their personal documents, and no admin access is needed to delete them. No one else should be able to see them—not even the admin. Only update the ledger that the user uploaded or deleted a personal document with its ID, no sensitive filename logged. In one word: personal vault is private for all users."
* **Instruction Prompt**:
  > "1. Add `is_personal` column to `documents`.  
  > 2. Create `/api/documents/personal/upload`, `/api/documents/personal/list`, and `/api/documents/personal/{id}` DELETE endpoints.  
  > 3. In the audit ledger, record action as `PERSONAL_UPLOAD` and `PERSONAL_DELETE` with doc ID, omitting raw filenames.  
  > 4. Ensure non-owners and administrators receive `HTTP 403 Forbidden` if attempting to view another user's personal vault."
* **What the Tool Produced**:
  - Implemented the personal upload endpoints.
  - In `GET /api/admin/documents`, the admin query did a `SELECT * FROM documents`, returning personal files in the administrator's document catalog.
* **What was Wrong / Security Analysis**:
  - **Privacy Violation**: Administrators could see the existence, titles, and IDs of employees' private personal files, violating the explicit requirement of complete privacy.
* **Engineering Action & Fix**:
  - Filtered all official catalog queries with `WHERE is_personal = 0`.
  - Scoped personal queries strictly to `WHERE is_personal = 1 AND owner_email = ?`.
  - Added test `test_personal_documents_isolation` in `backend/tests/test_documents.py` to verify that administrators cannot query personal files.
* **Commit Reference**: [`5a278fb`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/5a278fbd078331c3739c38242ce7ef357683e766)

---

## 🚀 Phase 5: 2FA Authentication, Hardening & Multi-Format Viewer

### Prompt Entry 5.1: 2FA Login OTP Delivery & Security Sanitization
* **Date**: October 24, 2026
* **System Prompt / Role**:
  > "Act as an Application Security Engineer specializing in Two-Factor Authentication (2FA) and Anti-Exfiltration Controls."
* **Context & Requirement Prompt**:
  > "1. Forget password: User receives a 5-min OTP on registered email to reset password.  
  > 2. 2FA Login: When existing user signs in, system sends a 5-min OTP to registered email. User must provide password + OTP.  
  > 3. No leakage: Never leak or autofill OTP codes into the UI or API response.  
  > 4. Professional pop-up notice when clicking download stating direct file downloading is prohibited."
* **Instruction Prompt**:
  > "1. Create `/api/send-login-otp` validating password before generating a 6-digit OTP with a 300-second expiration.  
  > 2. Configure Gmail SMTP on Port 465 SSL (`smtplib.SMTP_SSL`) with sender `guardfilespace@gmail.com`.  
  > 3. Ensure API responses return only confirmation text (`{"message": "OTP sent"}`), strictly omitting the secret.  
  > 4. Build custom modal alerts for logout confirmation and download prohibition."
* **What the Tool Produced**:
  - The tool initially returned the OTP code directly in the JSON response payload (`"otp_code": "194590"`) and wrote JavaScript that autofilled the `<input id="loginOtp">` field for "developer convenience."
* **What was Wrong / Security Analysis**:
  - **Complete 2FA Circumvention**: Returning the 2FA secret in the client response completely defeats the two-factor model by allowing API clients or XSS scripts to log in without accessing the victim's email inbox.
* **Engineering Action & Fix**:
  - Forcefully stripped `otp_code` from the response schemas in [`backend/routers/auth.py`](file:///c:/Users/MD%20ARSHAD/Desktop/Trust_valut_app/Trust_valut/backend/routers/auth.py).
  - Cleared all input values upon generation (`document.getElementById('loginOtp').value = ''`).
  - Added unit test `test_admin_login_success` asserting that valid credentials + verified database OTP succeed, while invalid OTPs are rejected.
* **Commit Reference**: [`23d2a13`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/23d2a131fbc09b66d08c41edcea4d9d0f9804264) & [`8d0a29b`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/8d0a29b50db040a53fbc27a0b8623ae55c92ac8f)

---

### Prompt Entry 5.2: Multi-Format Cryptographic In-Memory Preview
* **Date**: October 24, 2026
* **System Prompt / Role**:
  > "Act as a Senior Frontend Security Architect specializing in sandboxed in-memory rendering."
* **Context & Requirement Prompt**:
  > "As of now in the current application I am only able to view PDFs and not able to preview JPG and other file formats. I want to view all types of supported secure file formats without allowing users to download them."
* **Instruction Prompt**:
  > "1. In `backend/routers/documents.py`, dynamically detect file MIME types using `mimetypes.guess_type` and stream the correct `media_type`.  
  > 2. In `public/script.js`, refactor `viewDoc(id)` to inspect response headers:  
  >    - For Images (`.jpg`, `.jpeg`, `.png`, `.webp`): render via in-memory Blob URL in a context-disabled container.  
  >    - For Text (`.txt`, `.csv`, `.json`): escape HTML and render in a dark-mode monospace viewer.  
  >    - For PDFs: render page-by-page using PDF.js canvas sandboxes.  
  >    - For Office Docs (`.docx`, `.xlsx`, `.pptx`): show a zero-leak encrypted security envelope notice."
* **What the Tool Produced**:
  - The tool initially suggested adding an `<a href="..." download>Download to View</a>` button for images.
* **What was Wrong / Security Analysis**:
  - **Exfiltration Violation**: Trust Vault's core security mandate prohibits direct file downloads for non-owners. Providing a direct download link completely violates the read-only policy.
* **Engineering Action & Fix**:
  - Rejected the download button. Engineered an in-memory blob streaming pipeline that mounts images directly into a sandboxed `<img>` element with `oncontextmenu="return false;"` and user-selection disabled.
* **Commit Reference**: [`3054b0a`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/3054b0a0df3ea13dda4059dfabb871a96e29d84f)

---

## 📊 Summary of Critical Security Interventions

| Prompt Phase | Initial Tool Flaw | Vulnerability Type | Corrective Engineering Action | Verified Commit |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | Plain SHA-256 password hashing | Weak Cryptography | Replaced with salted **bcrypt** (`bcrypt.gensalt()`) | [`de97d5c`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/de97d5c806509fba24be7e382b60f5451ec3aa48) |
| **Phase 2** | Registration code displayed in admin table | Credential / Token Leakage | Masked code in UI; dispatched code directly via email | [`5a278fb`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/5a278fbd078331c3739c38242ce7ef357683e766) |
| **Phase 3** | Ledger cleanup endpoint (`DELETE /ledger`) | Audit Repudiation | Enforced strictly **append-only** audit ledger | [`5a278fb`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/5a278fbd078331c3739c38242ce7ef357683e766) |
| **Phase 3** | Root administrator could be deleted | Broken Access Control | Added hardcoded root admin delete protection | [`ac9c98d`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/ac9c98d533dc4fa708791bcbe885a7c12fae1dd5) |
| **Phase 4** | Personal vault files visible in admin catalog | Privacy Breach / Broken RBAC | Scoped admin catalog queries with `is_personal = 0` | [`5a278fb`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/5a278fbd078331c3739c38242ce7ef357683e766) |
| **Phase 5** | 2FA OTP returned in API response & autofilled | 2FA Authentication Bypass | Purged OTP from response; required out-of-band email | [`23d2a13`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/23d2a131fbc09b66d08c41edcea4d9d0f9804264) |
| **Phase 5** | Direct download links added for non-PDFs | Data Exfiltration | Built sandboxed in-memory blob viewer for images/text | [`3054b0a`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/3054b0a0df3ea13dda4059dfabb871a96e29d84f) |
