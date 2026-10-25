# 🔒 Trust Vault — Enterprise Cloud Document Vault & Security System

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Production%20Ready-009688.svg)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/Database-Turso%20libSQL-00eb84.svg)](https://turso.tech/)
[![Storage](https://img.shields.io/badge/Object%20Storage-Backblaze%20B2%20(S3)-red.svg)](https://www.backblaze.com/b2/)
[![Tests](https://img.shields.io/badge/Tests-19%20Passed%20(100%25)-brightgreen.svg)](https://docs.pytest.org/)
[![Deployment](https://img.shields.io/badge/Vercel-Live%20Production-black.svg)](https://trust-vault-gamma.vercel.app)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An enterprise-grade, cloud-native secure document management platform featuring **Two-Factor Authentication (2FA OTP)**, **Role-Based Access Control (RBAC)**, **Zero-Trust Whitelist Onboarding**, **Company Employee Active Roster Matching**, **Granular Permissions (View / Download / Edit)**, **In-App Document Editing with PDF Annotation**, **Multi-Layered Binary Magic-Byte Security**, **Zero-Leak In-Browser Document Inspection**, and an **Immutable Audit Ledger**.

---

## 🎯 About Trust Vault & Problem Solved

### The Problem
In modern organizations, confidential documents (financial records, legal agreements, compliance forms, employee data) are routinely shared over email threads, messaging apps, and static shared links. Once a file is sent:
1. **Control is completely lost** — recipients can forward, download, copy, and tamper with files without the owner knowing.
2. **Zero Audit Trail** — organizations have no verifiable proof of who viewed, downloaded, or altered a document.
3. **Weak Access Gates** — open registration portals allow unauthorized external users to sign up and view files.
4. **Malicious File Infiltration** — conventional uploads only check file extensions, allowing attackers to upload webshells and executables disguised as documents (`shell.php.pdf`).

### The Solution: Trust Vault
Trust Vault implements a comprehensive **Zero-Trust Enterprise Document Lifecycle**:
- **Strict Onboarding Approval**: No account can be created without admin whitelist authorization verified against active employee rosters.
- **Two-Factor Authentication (2FA)**: Every login and password reset is validated via a 5-minute single-use email OTP.
- **Granular Access Delegation**: View, Download, and In-App Edit rights are managed per document per user using iOS toggle switches.
- **Zero-Download DLP Protection**: Documents are decrypted in-memory and rendered into isolated canvas viewports; downloading is blocked by default.
- **In-App Editing & Annotations**: Users can annotate PDFs, edit text files inline, or apply image watermarks directly in the vault, with all edits automatically logged and notified to the administrator.
- **Immutable Ledger**: Every view, download, edit, and deletion is recorded in an append-only cryptographic audit log with CSV compliance export.

---

## 📑 Table of Contents

1. [📘 Complete User Guide (From Access Request to Daily Operations)](#-complete-user-guide-from-access-request-to-daily-operations)
   - [Phase 1: Submitting an Onboarding Request](#phase-1-submitting-an-onboarding-access-request)
   - [Phase 2: Administrator Roster Verification & Approval](#phase-2-administrator-roster-verification--approval)
   - [Phase 3: Registering Your Account with the Secure Code](#phase-3-registering-your-account-with-the-secure-code)
   - [Phase 4: Two-Factor Authentication (2FA) Sign In](#phase-4-two-factor-authentication-2fa-sign-in)
   - [Phase 5: Uploading & Storing Documents in Your Vault](#phase-5-uploading--storing-documents-in-your-vault)
   - [Phase 6: Searching Catalog & Requesting File Access](#phase-6-searching-the-document-catalog--requesting-access)
   - [Phase 7: Approving Requests with Granular iOS Toggle Switches](#phase-7-approving-incoming-requests-with-granular-permissions)
   - [Phase 8: In-App Document Inspection & Live Editing](#phase-8-in-app-document-inspection--live-editing)
   - [Phase 9: Managing User Profile & Password Resets](#phase-9-managing-profile--password-resets)
2. [🏛️ Technical Architecture & System Infrastructure](#️-technical-architecture--system-infrastructure)
3. [💡 System Strengths: Logical & Technical Highlights](#-system-strengths-logical--technical-highlights)
4. [🌐 Live Production Deployments & Admin Credentials](#-live-production-deployments--admin-credentials)
5. [🚀 Quickstart: Local Setup & Running Guide](#-quickstart-local-setup--running-guide)
6. [🧪 Automated Test Suite (100% Pass Rate)](#-automated-test-suite-100-pass-rate)
7. [🛡️ Complete API Reference](#️-complete-api-reference)
8. [📄 License](#-license)

---

## 📘 Complete User Guide (From Access Request to Daily Operations)

### Phase 1: Submitting an Onboarding Access Request
1. Open the application landing page at `index.html`.
2. Click on the **Request Access** tab.
3. Fill in your details:
   - **Corporate Work Email** (e.g., `user@company.com`)
   - **Full Name**
   - **Mobile / Phone Number**
   - **Department / Position** (e.g., *Engineering*, *Compliance*, *Finance*)
4. Click **Submit Request & Notify Admin**.
5. The system immediately places the request into `PENDING` state and automatically sends a notification email to the administrator containing your entered credentials.

---

### Phase 2: Administrator Roster Verification & Approval
1. The administrator logs into the **Admin Panel** (`admin.html`).
2. In the **👤 User Account Whitelist** table, the administrator reviews the pending request.
3. The table displays:
   - Candidate Details (Email, Name, Phone, Department).
   - **Company Roster Status Badge**: Automatically cross-referenced against the imported Active Employee Roster (`✓ Verified Company Employee` or `⚠ External / Not in Roster`).
4. The administrator clicks **Approve & Email Code** (or **Reject / Revoke**).
5. Upon approval, the backend generates a cryptographically random, single-use registration key (e.g., `TV-84A29F`) and emails it directly to the user.

---

### Phase 3: Registering Your Account with the Secure Code
1. Once you receive your approval email containing your **Secure Registration Code**, open `index.html` and click the **Register** tab.
2. Enter your registered email, full name, phone number, gender, and create a strong password.
3. Enter the exact **Secure Registration Code** received in your email.
4. Click **Create Verified Account**. The backend validates the code against the whitelist and creates your encrypted account.

---

### Phase 4: Two-Factor Authentication (2FA) Sign In
1. On the **Sign In** tab, enter your Email and Password, then click **📧 Send 5-Min Login OTP to My Email**.
   - *If your account is not yet registered, an interactive prompt will guide you to submit an access request.*
2. Check your email inbox for your 6-digit one-time passcode (OTP).
3. Enter the OTP into the verification box and click **Verify OTP & Sign In**.
4. The backend verifies the password hash and OTP expiration (valid for 300 seconds), then issues a signed JSON Web Token (JWT) that safely authorizes your session.

---

### Phase 5: Uploading & Storing Documents in Your Vault
1. Once logged in, navigate to the **My Vault** tab on the Dashboard (`dashboard.html`).
2. In the **Upload Secure Document** card, click **Choose File** and select your document (`.pdf`, `.docx`, `.xlsx`, `.pptx`, `.txt`, `.csv`, `.jpg`, `.png`, `.webp` up to 25MB).
3. Click **Upload Document**.
4. The backend runs the file through the **Triple-Layer Binary Magic-Byte Inspection Pipeline**:
   - Sanitizes the filename against directory traversal (`../`).
   - Verifies file signatures (ensuring a `.pdf` actually contains `%PDF-` binary headers).
   - Scans for embedded script payloads (`<?php`, `<script>`, `eval(`, `powershell -`).
5. Upon validation, the document is securely synced to cloud object storage (Backblaze B2) and recorded in the database and audit ledger.

---

### Phase 6: Searching the Document Catalog & Requesting Access
1. Click the **🔍 Document Catalog & Requests** tab.
2. Search through available company documents using the live search bar (filters by ID, filename, or owner).
3. If you do not have permission to view a document, click the **Request Access** button.
4. An automated access request is submitted, and an alert is emailed to the document owner notifying them of your request.

---

### Phase 7: Approving Incoming Requests with Granular Permissions
1. Document owners navigate to the **📥 Incoming Requests For My Docs** tab (administrators can also manage this via `admin.html`).
2. Next to the pending request, click the **⚙️ Permissions ▾** button.
3. Use the **iOS Toggle Switches** to customize exact permissions for the user:
   - **Can View** (toggle on/off): Enables zero-download in-memory canvas inspection.
   - **Can Download** (toggle on/off): Permits file download streaming.
   - **Can Edit** (toggle on/off): Permits in-app editing and document renaming.
4. Click **Apply Permissions** to save the granular access rule.
5. If access is rejected or revoked, click **Revoke / Reject Access**; the system immediately dispatches an email to the user informing them that their access was denied.

---

### Phase 8: In-App Document Inspection & Live Editing
1. In your **Accessible Documents** table, click **👁️ View** (or **👁️ View & Edit** if edit permissions were granted).
2. The document is fetched securely and decrypted in-memory:
   - **Zero-Download Protection**: Rendered onto an HTML5 canvas sandbox with right-click context menus and text copying disabled.
3. If you have Edit permissions, click **✏️ Edit Document**:
   - **PDF Documents**: Type text into the **PDF Annotation** field and check **Add Official Vault Stamp** to draw compliance headers and approval watermarks directly onto the PDF using `pdf-lib`.
   - **Plain Text / Code Files (`.txt`, `.csv`, `.json`, `.md`)**: Edit file contents live inside the built-in monospace editor.
   - **Image Documents (`.png`, `.jpg`, `.webp`)**: Apply filters (Normal, B&W, High Contrast) or type custom watermark text.
4. Click **💾 Save & Apply to Vault**. The edited file is validated and saved back into Vault storage. The audit columns (`last_edited_by` & `last_edited_at`) are updated, an entry is added to the system ledger, and an alert is sent to the administrator.

---

### Phase 9: Managing Profile & Password Resets
- **Profile Management**: Navigate to the **👤 Profile** tab to view your registered details, update your mobile number, and change your profile avatar.
- **Forgot Password**: If you forget your password, click **Reset Forgotten Password** on `index.html`. Enter your email to receive a 5-minute password reset OTP, verify the OTP, and set a new password securely.

---

## 🏛️ Technical Architecture & System Infrastructure

```
[ Modern Web Browser / Mobile Responsive UI ]
                     │  HTTPS / JWT Bearer
                     ▼
[ Vercel Edge Serverless / Cloud Application Layer ]
                     │
     ┌───────────────┼──────────────────────────────┐
     │               │                              │
     ▼               ▼                              ▼
[ 2FA & RBAC ]  [ Triple-Layer Validator ]   [ Out-of-Band Email Relay ]
Stateless JWT   Magic-Byte Inspection         Port 465 SSL SMTP Relay
Role Guards     WebShell/MZ/ELF Scanner       5-Min Single-Use OTPs
                     │                              │
     ┌───────────────┴──────────────────────────────┘
     ▼
[ Cloud Infrastructure Layer ]
     ├──► Turso libSQL: Distributed Cloud Database (Pipelined HTTP, Foreign Keys)
     └──► Backblaze B2: S3-Compatible Encrypted Cloud Object Storage
```

### Architectural Highlights
- **Backend Framework**: FastAPI (Python 3.11+) featuring asynchronous request routing, dependency injection (`Depends(get_db)`, `Depends(get_current_user)`), and Pydantic v2 data models.
- **Cloud Database (Turso libSQL)**: Distributed SQLite engine operated over HTTP pipelined connections with relational foreign key cascading and schema migrations.
- **Cloud Object Storage (Backblaze B2)**: S3-compatible cloud object store maintaining separation between official corporate documents and private personal vaults.
- **Email Delivery Gateway**: Multi-protocol transactional delivery through direct Port 465 SSL SMTP (`smtp.gmail.com`) delivering OTPs, whitelist codes, rejection notices, and candidate alerts worldwide.
- **Real-Time Client Synchronization**: Client scripts utilize `visibilitychange` event listeners and background polling to keep multiple browser tabs and windows synchronized without manual page refreshes.

---

## 💡 System Strengths: Logical & Technical Highlights

### 1. Logical Strengths (Business & Access Governance)
* **Dual-Tier Access Governance**:
  - *Tier 1 (Platform Whitelist & Candidate Credentials)*: Public visitors cannot create an account without administrator approval. Users submit their Work Email, Full Name, Mobile Number, and Department; an instant email alert is dispatched to the admin while their request is pending. Admins can import active company employee files (`.csv` / `.txt`) to verify roster status before approving. Upon admin approval, a single-use registration key (`TV-XXXXXX`) is automatically emailed to the applicant.
  - *Tier 2 (Per-Document Granular Permissions)*: Document owners and administrators can grant or revoke specific abilities using iOS toggle switches for **View**, **Download**, and **Edit**. Denied requests trigger automated rejection notices.
* **In-App Document Live Editing**:
  - **PDF Documents**: Direct in-app text annotation, notes, and official vault verification stamps via `pdf-lib` without leaving the browser.
  - **Plain Text / Code (`.txt`, `.csv`, `.json`, `.md`)**: Built-in real-time code/text editor with instant cloud save.
  - **Images (`.png`, `.jpg`, `.webp`)**: Sandboxed canvas filters and custom watermark stamps.
  - **Audit Logging**: Any user edits update `last_edited_by` & `last_edited_at` and trigger an immediate notification email to the administrator.
* **Zero-Leak Data Loss Prevention (DLP)**:
  - Direct file downloading is permanently blocked for non-authorized viewers.
  - Documents are rendered strictly in-memory using PDF.js `<canvas>` sandboxes and ephemeral blob URLs. Right-click context menus, text selection, and drag-and-drop file saves are disabled.
* **Non-Repudiation Audit Matrix**:
  - Every file upload, preview inspection, download, edit, rename, and deletion is recorded in an **append-only** audit ledger (`document_logs`).
  - No user or admin can alter or delete audit history through the API. Compliance exports are available as downloadable CSV files.

### 2. Technical Strengths (Engineering & Performance)
* **Triple-Layer Binary Magic-Byte Security**:
  - File extension checking is treated as untrusted metadata. The backend inspects leading file headers at the binary level (`%PDF-`, `\x89PNG`, `\xff\xd8\xff`, `PK\x03\x04`).
  - Deep scanning blocks Windows PE binaries (`MZ`), Linux ELF binaries (`\x7fELF`), and embedded script tags (`<?php`, `<script>`, `eval(`, `powershell -`). Double extensions (`file.pdf.exe`) are blocked immediately.
* **Resilient Out-of-Band Multi-Transport Email Relay**:
  - High-priority Port 465 implicit SSL SMTP relay through `smtp.gmail.com` delivers OTPs, credentials alerts, rejection notices, and security codes worldwide without sandbox limitations.
* **Serverless Cost Efficiency ($0 Running Cost)**:
  - Fully leverages cloud serverless primitives: Vercel Edge Serverless + Turso Distributed SQLite + Backblaze B2 S3 storage + Gmail SMTP. 100% cloud-native architecture with zero server maintenance overhead.
* **Sub-Second Parallel Client Loading**:
  - Frontend dashboard utilizes `Promise.allSettled()` to fetch user documents, catalog requests, personal files, and incoming requests in parallel without blocking.

---

## 🌐 Live Production Deployments & Admin Credentials
* **Live Deployment URL**: [https://trust-vault-gamma.vercel.app](https://trust-vault-gamma.vercel.app)
* **Alternative Render Deployment**: [https://trust-vault.onrender.com](https://trust-vault.onrender.com)
* **GitHub Repository**: [https://github.com/24jr5a0407-cell/Trust_Vault](https://github.com/24jr5a0407-cell/Trust_Vault)
* **Master Admin Credentials**:
  - Email: `guardfilespace@gmail.com`
  - Password: `Arshad@1234`
  - 2FA OTP: Dispatched to `guardfilespace@gmail.com` upon login request (valid for 5 minutes).

---

## 🚀 Quickstart: Local Setup & Running Guide

### 1. Clone the Repository
```bash
git clone https://github.com/24jr5a0407-cell/Trust_Vault.git
cd Trust_Vault
```

### 2. Set Up Virtual Environment & Dependencies
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment Variables (`.env`)
Create a `.env` file in the root directory (or use default mock/local fallbacks):
```env
# Master Administrator
ADMIN_EMAIL=guardfilespace@gmail.com

# Turso Cloud libSQL Database
TURSO_DATABASE_URL=libsql://trust-vault-24jr5a0407-cell.turso.io
TURSO_AUTH_TOKEN=<your_turso_auth_token>

# Backblaze B2 Cloud Object Storage (S3-Compatible)
B2_BUCKET_NAME=trust-vault-storage
B2_KEY_ID=<your_b2_key_id>
B2_APPLICATION_KEY=<your_b2_app_key>
B2_ENDPOINT_URL=https://s3.us-east-005.backblazeb2.com

# Gmail SMTP 2FA Relay (Port 465 SSL)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=guardfilespace@gmail.com
SMTP_PASSWORD=<your_gmail_app_password>
SMTP_FROM_EMAIL=guardfilespace@gmail.com
SMTP_FROM_NAME="Trust Vault Security"
```

### 4. Run Application Locally
```bash
uvicorn backend.main:app --reload --port 8000
```
Visit **http://127.0.0.1:8000/index.html** in your browser.

---

## 🧪 Automated Test Suite (100% Pass Rate)

Trust Vault includes comprehensive unit and integration test coverage across all layers:
```bash
python -m pytest backend/tests
```

```
collected 19 items
backend/tests/test_admin.py ...                                          [ 15%]
backend/tests/test_auth.py .....                                         [ 42%]
backend/tests/test_documents.py ....                                     [ 63%]
backend/tests/test_file_validation.py ......                             [ 94%]
backend/tests/test_requests.py .                                         [100%]

============================== 19 passed in ~0.5s ==============================
```

---

## 🛡️ Complete API Reference

| Endpoint | Method | Role / Guard | Description |
| :--- | :--- | :--- | :--- |
| `/api/request-access` | `POST` | Public | Submit onboarding email & credentials for admin approval. |
| `/api/register` | `POST` | Whitelisted | Register with pre-approved secure code (`TV-XXXXXX`). |
| `/api/send-login-otp` | `POST` | User | Authenticate credentials and send 5-minute Login OTP. |
| `/api/login` | `POST` | User | Verify OTP and issue JWT access token. |
| `/api/forgot-password` | `POST` | Public | Send 5-minute password reset OTP. |
| `/api/reset-password` | `POST` | Public | Reset password with valid OTP. |
| `/api/profile` | `GET` / `PUT` | Authenticated | View and update user profile, avatar, and phone. |
| `/api/documents/upload` | `POST` | User | Upload official enterprise file (magic-byte validated). |
| `/api/documents/` | `GET` | User | View accessible documents (owned or granted). |
| `/api/documents/{id}/preview` | `GET` | Granted User | Sandboxed in-memory preview (no download). |
| `/api/documents/{id}/download` | `GET` | Owner / Admin / Granted | Stream file download if explicitly permitted. |
| `/api/documents/{id}` | `PUT` | Owner / Admin / Granted | Rename document filename. |
| `/api/documents/{id}/content` | `PUT` | Owner / Admin / Granted | Overwrite document content in-app (PDF annotations, etc.). |
| `/api/documents/{id}` | `DELETE` | Admin Only | Delete document from database and B2 cloud storage. |
| `/api/documents/personal/upload` | `POST` | User | Upload private encrypted personal vault document. |
| `/api/admin/employees/import` | `POST` | Admin Only | Import company active users roster (`.csv` / `.txt`). |
| `/api/admin/requests` | `GET` | Admin Only | List access requests with company employee verification. |
| `/api/admin/action` | `POST` | Admin Only | Approve or revoke whitelist access (sends email code / rejection). |
| `/api/admin/ledger` | `GET` | Admin Only | Query immutable audit log with filters. |
| `/api/admin/ledger/export` | `GET` | Admin Only | Download CSV export of complete system audit ledger. |

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
