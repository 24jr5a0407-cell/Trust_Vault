# 📝 PROMPTS.md: Architectural Evolution & Decision Log

> **System**: Trust Vault  
> **Repository**: [https://github.com/24jr5a0407-cell/Trust_Vault](https://github.com/24jr5a0407-cell/Trust_Vault)  
> **Author**: `24jr5a0407-cell` (`24jr5a0407@gmail.com`)  
> **Requirement**: At least five dated entries documenting: what was asked for, what the automated tool produced, what was fundamentally wrong or insecure with it, and what was implemented instead with links to specific commits.

---

### Entry 1: 2FA Authentication & OTP Delivery Architecture
* **Date**: October 24, 2026
* **What was asked for**:
  "When the existing user is signing in the system the system should also send the otp so that the user use the otp and password to signin the system. 5-minute validity."
* **What the tool produced**:
  The tool initially generated an implementation that returned the plaintext 6-digit OTP inside the JSON response of `/api/send-login-otp` (`{"message": "OTP sent", "otp_code": "123456"}`) and automatically populated the client-side `<input id="loginOtp">` in `script.js` so "testing would be easier."
* **What was wrong with it (The Security Flaw)**:
  This was a complete architectural blunder. Returning the 2FA secret in the HTTP response and pre-filling it in the browser DOM defeated the entire purpose of Two-Factor Authentication. Any attacker sniffing the network or using an automated script would bypass 2FA without ever possessing access to the victim's email inbox.
* **What was done instead**:
  Strictly purged `otp_code` from the API response payload and removed all autofill DOM logic in `script.js`. The backend persists the OTP cryptographically with a 300-second UNIX timestamp in Turso and dispatches it out-of-band via Gmail SMTP over Port 465 SSL. The client interface remains completely blank until the user reads their email inbox.
* **Commit Link**:
  - [`23d2a13`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/23d2a131fbc09b66d08c41edcea4d9d0f9804264) — *fix(security): strictly remove OTP from API response and UI placeholder, requiring real email delivery*

---

### Entry 2: Whitelist Registration Codes & Admin Security Leak (Authorisation & Access Control)
* **Date**: October 24, 2026
* **What was asked for**:
  "At present the admin is not able to send the email to the user about his security code, implement the option of admin sending the email to the user to his registered email about the security code. Please not store the security code in the table."
* **What the tool produced**:
  The tool modified the database schema to completely drop the `secure_code` column from `allowed_users`, which immediately broke the user registration flow because `/api/register` had no record against which to validate the user's submitted registration token. Furthermore, the admin table was still rendering existing plaintext codes to any logged-in administrator.
* **What was wrong with it (The Security Flaw)**:
  1. Dropping the verification secret entirely made registration impossible or forced registration to proceed with zero authorization validation.
  2. Displaying raw codes in the UI meant anyone looking over an administrator's shoulder or any secondary admin could view and reuse the confidential onboarding tokens of new employees before they registered.
* **What was done instead**:
  Retained the code in the database for single-use cryptographic verification, but completely masked it on the API and UI layer (`secure_code_masked = "Sent to User's Email"`). Automated email dispatch sends the `TV-XXXXXX` code directly to the approved user's inbox upon administrator approval, keeping the admin table sanitized.
* **Commit Link**:
  - [`5a278fb`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/5a278fbd078331c3739c38242ce7ef357683e766) — *feat: implement 5-min OTP email 2FA, forgot password, email notifications, responsive UI, logout confirmation, and security enhancements*

---

### Entry 3: Primary Root Administrator Protection (Access Control & Privilege Escalation)
* **Date**: October 24, 2026
* **What was asked for**:
  "Make the admin mail as guardfilespace@gmail.com and remove guardfile@gmail.com."
* **What the tool produced**:
  A standard database query deleting the old user and updating the local configuration, but the endpoint `/api/admin/users/{email}` had a hardcoded bypass allowing any admin to delete any account without guarding the new root master email.
* **What was wrong with it (The Security Flaw)**:
  A secondary administrator account or a compromised administrative session could call `DELETE /api/admin/users/guardfilespace@gmail.com` and permanently delete the root master administrator, bricking administrative control of the vault.
* **What was done instead**:
  Implemented hardcoded root protection in `backend/routers/admin.py`:
  ```python
  if email == current_admin["email"] or email == "guardfilespace@gmail.com":
      raise HTTPException(status_code=400, detail="Cannot remove primary admin account.")
  ```
  Also added automated unit test `test_cannot_delete_primary_admin` in `backend/tests/test_admin.py` to ensure that any deletion attempt on the master administrator returns `HTTP 400 Bad Request`.
* **Commit Link**:
  - [`ac9c98d`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/ac9c98d533dc4fa708791bcbe885a7c12fae1dd5) — *refactor(auth): set guardfilespace@gmail.com as primary admin, remove 4th tab and integrate forgot password into standard login layout*

---

### Entry 4: Immutable Audit Trail & Non-Repudiation (Audit Trail Security)
* **Date**: October 24, 2026
* **What was asked for**:
  "When the admin or code owner approves the request send the simple notifications for the each action like permission granted and permission revoked etc... and log everything in the ledger."
* **What the tool produced**:
  A simple logging table with basic CRUD endpoints, including an endpoint to "clean up old logs" to save database space (`DELETE /api/admin/logs`).
* **What was wrong with it (The Security Flaw)**:
  Providing any mechanism to delete or alter logs violates the fundamental requirement of an enterprise **Audit Trail**. An insider who improperly viewed or exfiltrated a document could simply call the cleanup endpoint to erase their tracks, defeating non-repudiation.
* **What was done instead**:
  Enforced an **append-only architecture** on `document_logs`. Removed all deletion or update endpoints for audit records. Added database indexing on `(document_id, user_email)` for high-performance querying and implemented an immutable CSV export endpoint (`/api/admin/ledger/export`) so compliance officers can export audit trails to external cold storage or SIEM systems.
* **Commit Link**:
  - [`5a278fb`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/5a278fbd078331c3739c38242ce7ef357683e766) — *feat: implement 5-min OTP email 2FA, forgot password, email notifications, responsive UI, logout confirmation, and security enhancements*

---

### Entry 5: Multi-Format Cryptographic In-Memory Preview vs Native Browser Downloads
* **Date**: October 24, 2026
* **What was asked for**:
  "As of now in the current application im only able to view the pdfs and not able preview the jpg and other file formats i want to view all types of supported secure file formats."
* **What the tool produced**:
  The tool suggested adding standard `<a href="...">Download to View</a>` links for images and text documents so the browser could open them in separate tabs or download them directly to the user's hard drive.
* **What was wrong with it (The Security Flaw)**:
  Permitting direct file downloads or opening raw links in unprotected browser tabs violates the core Trust Vault security mandate: preventing unauthorized document exfiltration. Once a file is downloaded to a local disk, all access revocation and audit logging become meaningless.
* **What was done instead**:
  Engineered an in-memory multi-format viewer inside [`public/script.js`](file:///c:/Users/MD%20ARSHAD/Desktop/Trust_valut_app/Trust_valut/public/script.js#L430-L518). Images (`.jpg`, `.jpeg`, `.png`, `.webp`) are streamed as encrypted memory blobs and rendered inside an un-selectable, right-click disabled modal. Text files (`.txt`, `.csv`, `.json`) are safely escaped and displayed in a secure preformatted terminal. PDFs continue rendering via PDF.js canvas sandboxes. Direct file downloads remain prohibited.
* **Commit Link**:
  - [`3054b0a`](https://github.com/24jr5a0407-cell/Trust_Vault/commit/3054b0a0df3ea13dda4059dfabb871a96e29d84f) — *feat(viewer): implement multi-format in-browser secure preview for images, text, and pdfs with mime detection*
