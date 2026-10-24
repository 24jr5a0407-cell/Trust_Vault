# 🔒 Trust Vault — Enterprise Cloud Document Vault & Security System

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Production%20Ready-009688.svg)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/Database-Turso%20libSQL-00eb84.svg)](https://turso.tech/)
[![Storage](https://img.shields.io/badge/Object%20Storage-Backblaze%20B2%20(S3)-red.svg)](https://www.backblaze.com/b2/)
[![Tests](https://img.shields.io/badge/Tests-19%20Passed%20(100%25)-brightgreen.svg)](https://docs.pytest.org/)
[![Deployment](https://img.shields.io/badge/Vercel-Live%20Production-black.svg)](https://trust-vault-gamma.vercel.app)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An enterprise-grade, cloud-native secure document management platform featuring **Two-Factor Authentication (2FA OTP)**, **Role-Based Access Control (RBAC)**, **Zero-Trust Whitelist Onboarding**, **Multi-Layered Binary Magic-Byte Security**, **Zero-Leak In-Browser Document Inspection**, and an **Immutable Audit Ledger**.

Designed for high-concurrency cloud environments (100+ concurrent users + administrator) with zero server maintenance costs using serverless primitives.

---

## 🌐 Live Production Application
* **Live URL**: [https://trust-vault-gamma.vercel.app](https://trust-vault-gamma.vercel.app)
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
  - *Tier 1 (Platform Whitelist)*: Public visitors cannot create an account without administrator approval. Upon admin approval, a single-use registration key (`TV-XXXXXX`) is automatically emailed to the applicant.
  - *Tier 2 (Per-Document Granular Permissions)*: Approved users only see documents they own or have been specifically granted permission to inspect. Document owners and admins review access requests with one-click approvals or revocations.
* **Zero-Leak Data Loss Prevention (DLP)**:
  - Direct file downloading is permanently blocked for non-owners.
  - Documents are rendered strictly in-memory using PDF.js `<canvas>` sandboxes and memory object URLs. Right-click context menus, text selection, and drag-and-drop file saves are disabled.
* **Non-Repudiation Audit Matrix**:
  - Every file upload, preview inspection, download, and deletion is recorded in an **append-only** audit ledger (`document_logs`).
  - No user or admin can alter or delete audit history through the API. Compliance exports are available as downloadable CSV files.

### 2. Technical Strengths (Engineering & Performance)
* **Triple-Layer Binary Magic-Byte Security**:
  - File extension checking is treated as untrusted metadata. The backend inspects leading file headers at the binary level (`%PDF-`, `\x89PNG`, `\xff\xd8\xff`, `PK\x03\x04`).
  - Deep scanning blocks Windows PE binaries (`MZ`), Linux ELF binaries (`\x7fELF`), and embedded script tags (`<?php`, `<script>`, `eval(`, `powershell -`). Double extensions (`file.pdf.exe`) are blocked immediately.
* **Resilient Out-of-Band Multi-Transport Email Relay**:
  - High-priority Port 465 implicit SSL SMTP relay through `smtp.gmail.com` delivers OTPs and security codes to any recipient worldwide without sandbox limitations.
* **Serverless Cost Efficiency ($0 Running Cost)**:
  - Fully leverages cloud serverless primitives: Vercel Edge Serverless + Turso Distributed SQLite + Backblaze B2 S3 storage + Gmail SMTP. 100% cloud-native architecture with zero server maintenance overhead.
* **Sub-Second Parallel Client Loading**:
  - Frontend dashboard utilizes `Promise.allSettled()` to fetch user documents, catalog requests, personal files, and incoming reviews in parallel, eliminating sequential network blocking.

---

## 📂 Repository Security & Verification Documents

Alongside this codebase, thorough architectural and threat analysis documents are maintained:
* [**`THREATS.md`**](file:///c:/Users/MD%20ARSHAD/Desktop/Trust_valut_app/Trust_valut/THREATS.md): A comprehensive threat matrix detailing 8 realistic attack vectors (e.g. Broken Access Control, IDOR, Webshells, Screen Exfiltration), their implemented mitigations, and explicit accepted residual risks.
* [**`PROMPTS.md`**](file:///c:/Users/MD%20ARSHAD/Desktop/Trust_valut_app/Trust_valut/PROMPTS.md): Dated engineering log recording critical architectural decisions, security blunders caught during automated generation, and commit references.

---

## 🚀 Getting Started & Local Setup

### Prerequisites
* Python 3.11+
* Git

### Installation
```bash
# 1. Clone repository
git clone https://github.com/24jr5a0407-cell/Trust_Vault.git
cd Trust_Vault

# 2. Create virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
```

### Running Locally
```bash
# Start FastAPI backend server
cd backend
python -m uvicorn main:app --reload --port 8000
```
Open your browser and navigate to `http://localhost:8000`.

---

## 🧪 Automated Test Suite

Trust Vault includes an automated test suite verifying authorization, file security, access controls, and administrative protections:

```bash
# Run all tests with verbose output
python -m pytest backend/tests -v
```

### Test Coverage Breakdown
* `test_admin.py`: RBAC route protection, non-admin 403 Forbidden checks, primary administrator delete prevention.
* `test_auth.py`: 2FA login verification, invalid password rejection, whitelist onboarding lifecycle.
* `test_documents.py`: File upload, catalog search, preview authorization, and private vault data isolation.
* `test_file_validation.py`: Magic-byte validation, extension spoofing rejection, malicious webshell detection, dangerous double-extensions.
* `test_requests.py`: Document permission request submission, owner approval, and access revocation.

---

## 👥 Roles & Access Matrix

| Feature / Action | Anonymous Visitor | Approved User | Document Owner | Master Administrator |
| :--- | :---: | :---: | :---: | :---: |
| Submit Whitelist Request | ✅ | — | — | — |
| Complete 2FA Login | — | ✅ | ✅ | ✅ |
| Upload Official Document | — | ✅ | ✅ | ✅ |
| Preview Accessible Document | — | Restricted | ✅ | ✅ |
| Direct Download File | — | ❌ (Blocked) | ✅ | ✅ |
| Manage Private Vault Files | — | Personal Only | Personal Only | Personal Only |
| Approve / Revoke Document Access | — | ❌ | ✅ (Own Files) | ✅ (All Files) |
| Onboard Whitelist Users | — | ❌ | ❌ | ✅ |
| View & Export Audit Ledger | — | ❌ | ❌ | ✅ |
