# 🛡️ Trust Vault — Enterprise Cloud Document Vault & Security System

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Production%20Ready-009688.svg)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/Database-Turso%20libSQL-00eb84.svg)](https://turso.tech/)
[![Storage](https://img.shields.io/badge/Object%20Storage-Backblaze%20B2%20(S3)-red.svg)](https://www.backblaze.com/b2/)
[![Tests](https://img.shields.io/badge/Tests-19%20Passed%20(100%25)-brightgreen.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An enterprise-grade, cloud-native secure document management platform featuring **Role-Based Access Control (RBAC)**, **Zero-Trust Whitelist Onboarding**, **Multi-Layered Binary Magic-Byte Security**, **File-Manager Multi-Criteria Search**, and an **Immutable Audit Ledger**.

Designed for high-concurrency cloud environments (handling 100+ concurrent users + administrator) with zero server maintenance costs using serverless cloud primitives.

---

## 🏛️ System Architecture

```
[ Web Browser / Client UI ]
           │  HTTPS / JWT Bearer
           ▼
[ Vercel Edge Serverless / Cloud Application Layer ]
           │
           ├──► [ Enterprise JWT & RBAC Engine (Stateless Authentication) ]
           │
           ├──► [ Multi-Layer File Security & Magic-Byte Validator ]
           │        ├── Filename Sanitization & Traversal Blocker
           │        ├── Binary Signature Validator (%PDF-, \x89PNG, \xff\xd8\xff, PK\x03\x04)
           │        ├── WebShell & Executable Payload Scanner (MZ, ELF, PHP, Eval)
           │        └── Double-Extension Blocker
           │
           ├──► [ Turso Cloud libSQL / Distributed SQLite Engine ]
           │        └── Pipelined HTTP, Connection Pooling, Foreign Key Enforcement
           │
           └──► [ Backblaze B2 S3-Compatible Object Storage ]
                    └── Direct Memory Streaming (Official & User-Scoped Folders)
```

---

## ✨ Key Enterprise Capabilities

### 1. 🔐 Dual-Tier Security & Access Governance
- **Tier 1 (Platform Onboarding Whitelist)**: Visitors cannot register without administrator approval. Admin generates cryptographic secure codes (`TV-XXXXXX`) to authorize employee registration.
- **Tier 2 (Per-File Document Permissions)**: Users request access to specific documents in the catalog. Document owners and administrators review, approve, reject, or revoke read permissions individually.

### 2. 🛡️ Deep Binary Magic-Byte & Malware Validation
- Does **not** rely on file extensions alone (prevents extension spoofing like `malware.exe` renamed to `contract.pdf`).
- Inspects binary headers at byte level for PDF, PNG, JPEG, WebP, and Office OpenXML documents.
- Scans for embedded webshells (`<?php`, `eval(`, `base64_decode(`), XSS scripts (`<script>`), and Windows/Linux executable binaries (`MZ`, `ELF`).
- Rejects dangerous double-extensions (e.g. `invoice.pdf.exe`).

### 3. 🔍 File-Manager Search Engine
- Search by **Document ID** (`#4`, `#12`).
- Search by **Full Filename** or **Half / Partial Name** (case-insensitive substring match).
- Search by **Owner Name / Email** (e.g. `alice`, `admin`, `@company.com`).
- Instant client-side debounced filtering with live database synchronization.

### 4. 🔒 Zero-Trust File Protection & Audit Ledger
- **Private Personal Vault**: User-scoped confidential storage completely inaccessible to other users or administrators.
- **Watermarked In-Browser Preview**: Rendered securely on canvas without revealing direct storage paths.
- **Immutable Ledger**: Every view, download, rename, grant, or deletion is recorded with an immutable timestamp and actor email.

---

## 🚀 Technology Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) | High-performance asynchronous Python API with automatic OpenAPI documentation. |
| **Cloud Database** | [Turso](https://turso.tech/) (libSQL) | Distributed SQLite over HTTP with sub-30ms latency, zero lock contention, and WAL mode. |
| **Cloud Object Storage** | [Backblaze B2](https://www.backblaze.com/b2/) | Enterprise S3-compatible cloud bucket for high-speed multi-part file streaming. |
| **Authentication** | HMAC-SHA256 JWT | Stateless token verification with zero database query overhead. |
| **Frontend** | Vanilla JS / HTML5 / CSS3 / PDF.js | Zero-build client optimized for instantaneous page loads and low bandwidth consumption. |
| **Automated Testing** | Pytest & HTTPX | Full integration and security test suite covering 100% of critical paths. |

---

## 🧪 Automated Test Suite

Trust Vault includes comprehensive automated test coverage (19 passing unit, integration, and security tests):

```bash
# Run the complete test suite
python -m pytest backend/tests -v
```

### Test Coverage Highlights:
- **`test_auth.py`**: Whitelist submission, secure code validation, duplicate checks, login verification, token generation.
- **`test_admin.py`**: RBAC permission boundaries (`403 Forbidden` enforcement), admin user listing, ledger CSV exports.
- **`test_documents.py`**: Document uploads, permission checks, personal document isolation, preview/download access.
- **`test_file_validation.py`**: Magic-byte verification, spoofed extension detection, webshell blocking, empty file rejection, double-extension prevention.
- **`test_requests.py`**: Full request lifecycle (request access, approve, grant access, revoke access).

---

## 🛠️ Local Installation & Development

### 1. Clone the repository
```bash
git clone https://github.com/24jr5a0407-cell/Trust_Vault.git
cd Trust_Vault
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Start the Application
```bash
python -m uvicorn backend.main:app --reload --port 8000
```
- Web Application: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Interactive API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## ☁️ Zero-Cost Production Deployment to Vercel

Trust Vault is configured out-of-the-box for serverless deployment on Vercel:

1. Push this repository to your GitHub account: `https://github.com/24jr5a0407-cell/Trust_Vault`.
2. Log into [Vercel](https://vercel.com/) with your GitHub account.
3. Click **Add New Project** and select `Trust_Vault`.
4. Under **Environment Variables**, add the keys from your `.env` file:
   - `TURSO_DATABASE_URL`
   - `TURSO_AUTH_TOKEN`
   - `B2_BUCKET_NAME`
   - `B2_KEY_ID`
   - `B2_APPLICATION_KEY`
   - `B2_ENDPOINT_URL`
   - `JWT_SECRET_KEY`
   - `ADMIN_EMAIL`
   - `ADMIN_DEFAULT_PASSWORD`
   - `MAX_UPLOAD_SIZE_MB`
5. Click **Deploy**. Vercel will automatically build the static frontend and Python serverless API.

---

## 📄 License
Distributed under the MIT License.
