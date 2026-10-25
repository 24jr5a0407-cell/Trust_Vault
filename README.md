# 🔒 Trust Vault — Enterprise Cloud Document Vault & Security System

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Production%20Ready-009688.svg)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/Database-Turso%20libSQL-00eb84.svg)](https://turso.tech/)
[![Storage](https://img.shields.io/badge/Object%20Storage-Backblaze%20B2%20(S3)-red.svg)](https://www.backblaze.com/b2/)
[![Tests](https://img.shields.io/badge/Tests-19%20Passed%20(100%25)-brightgreen.svg)](https://docs.pytest.org/)
[![Deployment](https://img.shields.io/badge/Vercel-Live%20Production-black.svg)](https://trust-vault-gamma.vercel.app)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An enterprise-grade, cloud-native secure document management platform featuring **Two-Factor Authentication (2FA OTP)**, **Role-Based Access Control (RBAC)**, **Zero-Trust Whitelist Onboarding**, **Company Employee Active Roster Matching**, **Granular Permissions (View / Download / Edit)**, **In-App Document Editing with PDF Annotation**, **Multi-Layered Binary Magic-Byte Security**, **Zero-Leak In-Browser Document Inspection**, and an **Immutable Audit Ledger**.

Designed for high-concurrency cloud environments (100+ concurrent users + administrator) with zero server maintenance costs using serverless primitives.

---

## 🌐 Live Production Application
* **Live Deployment URL**: [https://trust-vault-gamma.vercel.app](https://trust-vault-gamma.vercel.app)
* **Alternative Render Deployment**: [https://trust-vault.onrender.com](https://trust-vault.onrender.com)
* **GitHub Repository**: [https://github.com/24jr5a0407-cell/Trust_Vault](https://github.com/24jr5a0407-cell/Trust_Vault)
* **Master Admin Credentials**:
  - Email: `guardfilespace@gmail.com`
  - Password: `Arshad@1234`
  - 2FA OTP: Dispatched to `guardfilespace@gmail.com` upon login request (valid for 5 minutes).

---

## 🏛️ System Architecture

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

---

## 💡 System Strengths: Technical & Logical Highlights

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
