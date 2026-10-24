// Dynamic Production & Localhost API Base Resolution
const API_BASE = (window.location.origin && !window.location.origin.startsWith('file:') && !window.location.origin.includes(':8000'))
    ? `${window.location.origin}/api`
    : 'http://127.0.0.1:8000/api';

function authFetch(url, options = {}) {
    const token = localStorage.getItem('jwt_token');
    const headers = options.headers ? { ...options.headers } : {};
    if (token && !headers['Authorization']) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return fetch(url, { ...options, headers });
}

function showAlert(message, type = "success", containerId = "alertBox") {
    const box = document.getElementById(containerId);
    if (!box) return;
    box.className = `alert ${type}`;
    box.innerText = message;
    setTimeout(() => { box.className = ""; box.innerText = ""; }, 5000);
}

// --- GLOBAL CUSTOM APP MODAL (Alerts & Confirmations) ---
function showAppModal({ title, message, okText = "OK", cancelText = null, onOk = null, onCancel = null }) {
    const modal = document.getElementById('appModal');
    if (!modal) {
        if (cancelText) {
            if (confirm(`${title}\n\n${message}`) && onOk) onOk();
        } else {
            alert(`${title}\n\n${message}`);
            if (onOk) onOk();
        }
        return;
    }

    document.getElementById('appModalTitle').innerText = title;
    document.getElementById('appModalMessage').innerText = message;

    const btnContainer = document.getElementById('appModalButtons');
    btnContainer.innerHTML = '';

    if (cancelText) {
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'btn-secondary';
        cancelBtn.innerText = cancelText;
        cancelBtn.style.width = 'auto';
        cancelBtn.onclick = () => {
            closeAppModal();
            if (onCancel) onCancel();
        };
        btnContainer.appendChild(cancelBtn);
    }

    const okBtn = document.createElement('button');
    okBtn.innerText = okText;
    okBtn.style.width = 'auto';
    okBtn.onclick = () => {
        closeAppModal();
        if (onOk) onOk();
    };
    btnContainer.appendChild(okBtn);

    modal.style.display = 'flex';
}

function closeAppModal() {
    const modal = document.getElementById('appModal');
    if (modal) modal.style.display = 'none';
}

// Requirement 8: Professional message when clicking download
function showDownloadDisabledWarning() {
    showAppModal({
        title: "🛡️ Direct Download Prohibited",
        message: "Trust Vault Enterprise Security Policy prohibits direct file downloading to prevent unauthorized data exfiltration. All documents are restricted to secure, in-browser cryptographic read-only inspection."
    });
}

// Requirement 5: Logout Confirmation
function confirmLogout() {
    showAppModal({
        title: "🔒 Confirm Sign Out",
        message: "Are you sure you want to end your secure session and log out of Trust Vault?",
        okText: "Yes, Log Out",
        cancelText: "Cancel",
        onOk: () => {
            localStorage.clear();
            window.location.href = 'index.html';
        }
    });
}

function logout() {
    confirmLogout();
}

// --- AUTH TABS (Sign In, Register, Request Access, Forgot Password) ---
function switchTab(tab) {
    const tabs = ['login', 'register', 'request', 'forgot'];
    tabs.forEach(t => {
        const formEl = document.getElementById(`form${t.charAt(0).toUpperCase() + t.slice(1)}`);
        const tabBtn = document.getElementById(`tab${t.charAt(0).toUpperCase() + t.slice(1)}`);
        if (formEl) formEl.style.display = (tab === t) ? 'block' : 'none';
        if (tabBtn) {
            tabBtn.style.borderBottom = (tab === t) ? '2px solid var(--primary)' : 'none';
            tabBtn.style.color = (tab === t) ? 'var(--text-main)' : 'var(--text-muted)';
        }
    });

    // If navigating to forgot password, highlight login or clear active indicators
    if (tab === 'forgot') {
        const tabLogin = document.getElementById('tabLogin');
        if (tabLogin) {
            tabLogin.style.borderBottom = 'none';
            tabLogin.style.color = 'var(--text-muted)';
        }
    }
}

// --- STEP 1: SEND LOGIN 2FA OTP ---
async function handleSendLoginOtp() {
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;

    if (!email || !password) {
        showAlert("Please enter your email and password first.", "error");
        return;
    }

    const reqBtn = document.getElementById('btnRequestLoginOtp');
    if (reqBtn) {
        reqBtn.disabled = true;
        reqBtn.innerText = "⏳ Generating & Sending OTP...";
    }

    try {
        const res = await authFetch(`${API_BASE}/send-login-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to dispatch login OTP");

        showAlert(data.message, 'success');
        document.getElementById('loginOtpRequestSection').style.display = 'none';
        document.getElementById('loginOtpInputSection').style.display = 'block';
        document.getElementById('loginOtp').value = '';
        document.getElementById('loginOtp').focus();
    } catch (err) {
        showAlert(err.message, 'error');
        if (reqBtn) {
            reqBtn.disabled = false;
            reqBtn.innerText = "📧 Send 5-Min Login OTP to My Email";
        }
    }
}

// --- STEP 2: VERIFY OTP AND COMPLETE LOGIN ---
async function handleLogin() {
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    const otp = (document.getElementById('loginOtp')?.value || '').trim();

    if (!otp) {
        showAlert("Please enter the 6-digit OTP code sent to your email.", "error");
        return;
    }

    try {
        const res = await authFetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, otp })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Login failed");

        localStorage.setItem('user_email', data.email);
        localStorage.setItem('is_admin', data.is_admin);
        if (data.access_token) {
            localStorage.setItem('jwt_token', data.access_token);
        }
        window.location.href = 'dashboard.html';
    } catch (err) {
        showAlert(err.message, 'error');
    }
}

// --- REGISTER ---
async function handleRegister() {
    const email = document.getElementById('regEmail').value.trim();
    const secure_code = document.getElementById('regCode').value.trim();
    const password = document.getElementById('regPassword').value;

    try {
        const res = await authFetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, secure_code, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Registration failed");

        showAlert(data.message, 'success');
        switchTab('login');
    } catch (err) {
        showAlert(err.message, 'error');
    }
}

// --- REQUEST ACCESS ---
async function handleRequestAccess() {
    const email = document.getElementById('reqEmail').value.trim();

    try {
        const res = await authFetch(`${API_BASE}/request-access`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Request failed");

        showAlert(data.message, 'success');
    } catch (err) {
        showAlert(err.message, 'error');
    }
}

// --- FORGOT PASSWORD (STEP 1: SEND OTP) ---
async function handleSendForgotOtp() {
    const email = document.getElementById('forgotEmail').value.trim();
    if (!email) {
        showAlert("Please enter your registered email address.", "error");
        return;
    }

    const btn = document.getElementById('btnSendForgotOtp');
    if (btn) {
        btn.disabled = true;
        btn.innerText = "⏳ Generating & Sending Reset OTP...";
    }

    try {
        const res = await authFetch(`${API_BASE}/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to send reset OTP");

        showAlert(data.message, 'success');
        document.getElementById('forgotStep1').style.display = 'none';
        document.getElementById('forgotStep2').style.display = 'block';
        document.getElementById('resetOtp').value = '';
        document.getElementById('resetOtp').focus();
    } catch (err) {
        showAlert(err.message, 'error');
        if (btn) {
            btn.disabled = false;
            btn.innerText = "Send Password Reset OTP";
        }
    }
}

// --- FORGOT PASSWORD (STEP 2: RESET WITH OTP) ---
async function handleResetPassword() {
    const email = document.getElementById('forgotEmail').value.trim();
    const otp = (document.getElementById('resetOtp')?.value || '').trim();
    const new_password = document.getElementById('newPassword').value;

    if (!otp || !new_password) {
        showAlert("Please enter both the OTP from your email and your new password.", "error");
        return;
    }

    try {
        const res = await authFetch(`${API_BASE}/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, otp, new_password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Password reset failed");

        showAlert(data.message, 'success');
        setTimeout(() => {
            switchTab('login');
            document.getElementById('loginEmail').value = email;
            document.getElementById('loginPassword').value = new_password;
        }, 1500);
    } catch (err) {
        showAlert(err.message, 'error');
    }
}

// --- DASHBOARD LOADERS ---
async function checkAuthAndLoadDashboard() {
    const email = localStorage.getItem('user_email');
    const isAdmin = localStorage.getItem('is_admin') === 'true';

    if (!email) {
        window.location.href = 'index.html';
        return;
    }

    document.getElementById('userWelcome').innerText = `Logged in as: ${email}`;
    if (isAdmin) {
        document.getElementById('adminNavBtn').style.display = 'inline-block';
    }

    // Parallel fetch for speed & performance optimization
    await Promise.allSettled([
        loadUserDocuments(),
        loadCatalog(),
        loadMyRequests(),
        loadDashboardIncomingRequests(),
        loadPersonalDocuments()
    ]);
}

// DASHBOARD TABS
function switchDashboardTab(tab) {
    const sections = ['vault', 'catalog', 'incoming', 'personal'];
    sections.forEach(s => {
        const secEl = document.getElementById(`section${s.charAt(0).toUpperCase() + s.slice(1)}`);
        const tabBtn = document.getElementById(`tab${s.charAt(0).toUpperCase() + s.slice(1)}`);
        if (secEl) secEl.style.display = (tab === s) ? 'block' : 'none';
        if (tabBtn) {
            tabBtn.style.background = (tab === s) ? 'var(--primary)' : '#64748b';
        }
    });
}

// --- MY VAULT DOCUMENTS ---
let userVaultDocumentsCache = [];

function renderVaultTable(docs) {
    const tbody = document.getElementById('documentTableBody');
    if (!tbody) return;
    if (!docs || docs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No matching documents found.</td></tr>`;
        return;
    }
    tbody.innerHTML = docs.map(doc => `
        <tr>
            <td><strong>#${doc.id}</strong></td>
            <td>${doc.filename}</td>
            <td>${doc.owner_email}</td>
            <td>${new Date(doc.created_at).toLocaleString()}</td>
            <td>
                <button onclick="viewDoc(${doc.id})" class="btn-secondary" style="padding: 5px 10px; font-size: 0.8rem; width: auto !important;">View</button>
                <button onclick="showDownloadDisabledWarning()" class="btn-secondary" style="padding: 5px 10px; font-size: 0.8rem; background: #64748b; width: auto !important;">Download</button>
            </td>
        </tr>
    `).join('');
}

function filterVaultDocuments() {
    const query = (document.getElementById('vaultSearchInput')?.value || '').toLowerCase().trim();
    if (!query) {
        renderVaultTable(userVaultDocumentsCache);
        return;
    }
    const filtered = userVaultDocumentsCache.filter(doc => 
        doc.id.toString().includes(query) ||
        (doc.filename && doc.filename.toLowerCase().includes(query)) ||
        (doc.owner_email && doc.owner_email.toLowerCase().includes(query))
    );
    renderVaultTable(filtered);
}

function clearVaultSearch() {
    const input = document.getElementById('vaultSearchInput');
    if (input) input.value = '';
    renderVaultTable(userVaultDocumentsCache);
}

async function loadUserDocuments() {
    const email = localStorage.getItem('user_email');
    const tbody = document.getElementById('documentTableBody');
    if (!tbody) return;

    try {
        const res = await authFetch(`${API_BASE}/documents/?user_email=${encodeURIComponent(email)}`);
        const docs = await res.json();
        userVaultDocumentsCache = Array.isArray(docs) ? docs : [];
        renderVaultTable(userVaultDocumentsCache);
    } catch (err) {
        console.error("Error loading user documents:", err);
    }
}

async function uploadDocument() {
    const fileInput = document.getElementById('uploadFile');
    const email = localStorage.getItem('user_email');

    if (fileInput.files.length === 0) {
        showAlert("Please select a file to upload.", "error");
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("owner_email", email);

    try {
        const res = await authFetch(`${API_BASE}/documents/upload`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Upload failed");

        showAlert("Document uploaded successfully!", "success");
        fileInput.value = "";
        loadUserDocuments();
    } catch (err) {
        showAlert(err.message, "error");
    }
}

// Configure PDF.js worker source
if (typeof pdfjsLib !== 'undefined') {
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
}

// --- SECURE IN-BROWSER DOCUMENT VIEWER ---
async function viewDoc(id) {
    const email = localStorage.getItem('user_email');
    const token = localStorage.getItem('jwt_token') || '';
    const previewUrl = `${API_BASE}/documents/${id}/preview?user_email=${encodeURIComponent(email)}&token=${encodeURIComponent(token)}`;
    
    document.getElementById('previewTitle').innerText = `Secure Cryptographic Viewer (ID: #${id}) - Read Only`;
    document.getElementById('previewModal').style.display = 'flex';
    
    const container = document.getElementById('pdfViewerContainer');
    container.innerHTML = '<p style="color: white; margin-top: 50px;">Decrypting and rendering document in memory...</p>';

    try {
        if (typeof pdfjsLib === 'undefined') {
            throw new Error("PDF rendering engine loading, please retry in a moment.");
        }
        const loadingTask = pdfjsLib.getDocument(previewUrl);
        const pdfDoc = await loadingTask.promise;
        container.innerHTML = '';

        for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
            const page = await pdfDoc.getPage(pageNum);
            const scale = 1.35;
            const viewport = page.getViewport({ scale: scale });

            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.height = viewport.height;
            canvas.width = viewport.width;
            canvas.style.boxShadow = '0 4px 6px rgba(0,0,0,0.3)';
            canvas.style.marginBottom = '12px';
            canvas.style.backgroundColor = 'white';
            canvas.style.maxWidth = '100%';
            canvas.style.height = 'auto';

            container.appendChild(canvas);

            await page.render({
                canvasContext: context,
                viewport: viewport
            }).promise;
        }
    } catch (err) {
        container.innerHTML = `<p style="color: #f87171; margin-top: 50px;">Preview Notice: Document rendered securely in-memory. (${err.message})</p>`;
    }
}

function closePreview() {
    document.getElementById('previewModal').style.display = 'none';
    document.getElementById('pdfViewerContainer').innerHTML = '';
}

// --- ADMIN CONTROL PANEL FUNCTIONS ---
async function checkAdminAuthAndLoad() {
    const isAdmin = localStorage.getItem('is_admin') === 'true';
    if (!isAdmin) {
        alert("Access denied. Admin privileges required.");
        window.location.href = 'dashboard.html';
        return;
    }
    await Promise.allSettled([
        loadAdminRequests(),
        loadAdminUsers(),
        loadAdminDocuments(),
        loadAdminLedger(),
        loadIncomingRequests()
    ]);
}

// Requirement 2: Do not display raw security codes in table
async function loadAdminRequests() {
    const tbody = document.getElementById('requestsTableBody');
    if (!tbody) return;
    try {
        const res = await authFetch(`${API_BASE}/admin/requests`);
        const reqs = await res.json();

        tbody.innerHTML = reqs.map(r => {
            const isAdmin = r.email === 'guardfilespace@gmail.com' || r.secure_code === 'ADMIN-MASTER-KEY';
            const isProcessed = r.status === 'APPROVED' || r.status === 'REJECTED';

            let actionHtml = '';
            if (isAdmin) {
                actionHtml = '<span style="color: var(--text-muted); font-size: 0.85rem;">System Admin</span>';
            } else if (isProcessed) {
                actionHtml = `<span style="color: var(--text-muted); font-size: 0.85rem;">Completed (${r.status})</span>`;
            } else {
                actionHtml = `
                    <button onclick="updateRequestStatus('${r.email}', 'APPROVED')" style="padding: 4px 8px; background: #22c55e; width: auto !important;">Approve & Email Code</button>
                    <button onclick="updateRequestStatus('${r.email}', 'REJECTED')" class="danger" style="padding: 4px 8px; width: auto !important;">Reject</button>
                `;
            }

            const codeDisplay = r.secure_code_masked || (r.email === 'guardfilespace@gmail.com' ? 'ADMIN-MASTER-KEY' : 'Sent via Email');

            return `
                <tr>
                    <td>${r.id}</td>
                    <td><strong>${r.email}</strong></td>
                    <td><span class="badge ${r.status.toLowerCase()}">${r.status}</span></td>
                    <td><span style="font-family: monospace; color: #4f46e5;">${codeDisplay}</span></td>
                    <td>${new Date(r.created_at).toLocaleString()}</td>
                    <td>${actionHtml}</td>
                </tr>
            `;
        }).join('');
    } catch (err) { console.error(err); }
}

async function updateRequestStatus(email, status) {
    try {
        const res = await authFetch(`${API_BASE}/admin/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, status })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        showAlert(data.message, 'success');
        loadAdminRequests();
        loadAdminUsers();
    } catch (err) {
        showAlert(err.message, 'error');
    }
}

async function loadAdminUsers() {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;
    try {
        const res = await authFetch(`${API_BASE}/admin/users`);
        const users = await res.json();

        tbody.innerHTML = users.map(u => `
            <tr>
                <td>${u.id}</td>
                <td><strong>${u.email}</strong></td>
                <td>${u.is_admin ? '<span class="badge approved">Yes</span>' : '<span class="badge">No</span>'}</td>
                <td>${new Date(u.created_at).toLocaleString()}</td>
                <td>
                    ${(u.email !== 'guardfilespace@gmail.com' && !u.is_admin) ? `<button onclick="removeUser('${u.email}')" class="danger" style="padding: 4px 8px; font-size: 0.8rem; width: auto !important;">Remove User</button>` : '<span style="color: var(--text-muted); font-size: 0.85rem;">Primary Admin</span>'}
                </td>
            </tr>
        `).join('');
    } catch (err) { console.error(err); }
}

async function removeUser(email) {
    showAppModal({
        title: "Remove User Account",
        message: `Are you sure you want to remove user account '${email}'? All active document permissions will be cleaned.`,
        okText: "Remove User",
        cancelText: "Cancel",
        onOk: async () => {
            try {
                const res = await authFetch(`${API_BASE}/admin/users/${encodeURIComponent(email)}`, {
                    method: 'DELETE'
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail);
                showAlert(data.message, 'success');
                loadAdminUsers();
                loadAdminDocuments();
            } catch (err) {
                showAlert(err.message, 'error');
            }
        }
    });
}

let adminDocsCache = [];

function renderAdminDocsTable(docs) {
    const tbody = document.getElementById('adminDocsTableBody');
    if (!tbody) return;
    if (!docs || docs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No documents found.</td></tr>`;
        return;
    }
    tbody.innerHTML = docs.map(d => `
        <tr>
            <td><strong>#${d.id}</strong></td>
            <td>${d.filename}</td>
            <td>${d.owner_email}</td>
            <td>${new Date(d.created_at).toLocaleString()}</td>
        </tr>
    `).join('');
}

function filterAdminDocs() {
    const query = (document.getElementById('adminDocSearchInput')?.value || '').toLowerCase().trim();
    if (!query) {
        renderAdminDocsTable(adminDocsCache);
        return;
    }
    const filtered = adminDocsCache.filter(doc => 
        doc.id.toString().includes(query) ||
        (doc.filename && doc.filename.toLowerCase().includes(query)) ||
        (doc.owner_email && doc.owner_email.toLowerCase().includes(query))
    );
    renderAdminDocsTable(filtered);
}

function clearAdminDocSearch() {
    const input = document.getElementById('adminDocSearchInput');
    if (input) input.value = '';
    renderAdminDocsTable(adminDocsCache);
}

async function loadAdminDocuments() {
    const tbody = document.getElementById('adminDocsTableBody');
    if (!tbody) return;
    try {
        const res = await authFetch(`${API_BASE}/admin/documents`);
        const docs = await res.json();
        adminDocsCache = Array.isArray(docs) ? docs : [];
        renderAdminDocsTable(adminDocsCache);
    } catch (err) { console.error("Error loading admin documents:", err); }
}

async function loadAdminLedger() {
    const emailFilter = document.getElementById('filterEmail')?.value || '';
    const actionFilter = document.getElementById('filterAction')?.value || '';
    const tbody = document.getElementById('auditTableBody');
    if (!tbody) return;

    try {
        let url = `${API_BASE}/admin/ledger?`;
        if (emailFilter) url += `user_email=${encodeURIComponent(emailFilter)}&`;
        if (actionFilter) url += `action=${encodeURIComponent(actionFilter)}`;

        const res = await authFetch(url);
        const logs = await res.json();

        if (!logs || logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No audit logs found.</td></tr>`;
            return;
        }

        tbody.innerHTML = logs.map(l => `
            <tr>
                <td><strong>#${l.id}</strong></td>
                <td>${l.filename} (ID: #${l.document_id})</td>
                <td>${l.user_email}</td>
                <td><span class="badge" style="background: #e2e8f0; color: #0f172a;">${l.action}</span></td>
                <td>${new Date(l.timestamp).toLocaleString()}</td>
            </tr>
        `).join('');
    } catch (err) { console.error(err); }
}

function exportLedgerCsv() {
    const token = localStorage.getItem('jwt_token') || '';
    window.location.href = `${API_BASE}/admin/ledger/export?token=${encodeURIComponent(token)}`;
}

// --- CATALOG & USER REQUESTS ---
let catalogDocumentsCache = [];
let catalogDebounceTimer = null;

function updateCatalogBadge(shown, total) {
    const badge = document.getElementById('catalogCountBadge');
    if (badge) {
        badge.innerText = `Showing ${shown} of ${total} files`;
    }
}

function handleCatalogSearchInput() {
    const query = (document.getElementById('searchInput')?.value || '').toLowerCase().trim();
    if (!query) {
        renderCatalogTable(catalogDocumentsCache);
        updateCatalogBadge(catalogDocumentsCache.length, catalogDocumentsCache.length);
        return;
    }
    const filtered = catalogDocumentsCache.filter(doc => 
        doc.id.toString().includes(query) ||
        (doc.filename && doc.filename.toLowerCase().includes(query)) ||
        (doc.owner_email && doc.owner_email.toLowerCase().includes(query))
    );
    renderCatalogTable(filtered);
    updateCatalogBadge(filtered.length, catalogDocumentsCache.length);

    clearTimeout(catalogDebounceTimer);
    catalogDebounceTimer = setTimeout(() => {
        searchCatalog();
    }, 400);
}

function clearCatalogSearch() {
    const input = document.getElementById('searchInput');
    if (input) input.value = '';
    loadCatalog();
}

function renderCatalogTable(docs) {
    const tbody = document.getElementById('catalogTableBody');
    if (!tbody) return;
    if (!docs || docs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No documents match your search.</td></tr>`;
        return;
    }

    const currentEmail = localStorage.getItem('user_email');
    tbody.innerHTML = docs.map(doc => {
        const isOwner = doc.owner_email === currentEmail;
        let actionBtn = '';
        if (isOwner) {
            actionBtn = `<span style="color: var(--text-muted); font-size: 0.85rem;">Document Owner</span>`;
        } else if (doc.request_status === 'APPROVED') {
            actionBtn = `
                <button onclick="viewDoc(${doc.id})" class="btn-secondary" style="padding: 4px 8px; font-size: 0.8rem; width: auto !important;">View</button>
                <button onclick="showDownloadDisabledWarning()" class="btn-secondary" style="padding: 4px 8px; font-size: 0.8rem; background: #64748b; width: auto !important;">Download</button>
            `;
        } else if (doc.request_status === 'PENDING') {
            actionBtn = `<span class="badge pending">Request Pending</span>`;
        } else {
            actionBtn = `<button onclick="requestAccess(${doc.id})" style="padding: 4px 8px; font-size: 0.8rem; width: auto !important;">Request Access</button>`;
        }

        return `
            <tr>
                <td><strong>#${doc.id}</strong></td>
                <td>${doc.filename}</td>
                <td>${doc.owner_email}</td>
                <td><span class="badge ${(doc.request_status || 'none').toLowerCase()}">${doc.request_status || 'NOT REQUESTED'}</span></td>
                <td>${actionBtn}</td>
            </tr>
        `;
    }).join('');
}

async function loadCatalog() {
    const email = localStorage.getItem('user_email');
    const tbody = document.getElementById('catalogTableBody');
    if (!tbody) return;

    try {
        const res = await authFetch(`${API_BASE}/requests/search?query=&user_email=${encodeURIComponent(email)}`);
        const docs = await res.json();
        catalogDocumentsCache = Array.isArray(docs) ? docs : [];
        renderCatalogTable(catalogDocumentsCache);
        updateCatalogBadge(catalogDocumentsCache.length, catalogDocumentsCache.length);
    } catch (err) { console.error("Error loading catalog:", err); }
}

async function searchCatalog() {
    const query = document.getElementById('searchInput')?.value.trim() || '';
    const email = localStorage.getItem('user_email');

    try {
        const res = await authFetch(`${API_BASE}/requests/search?query=${encodeURIComponent(query)}&user_email=${encodeURIComponent(email)}`);
        const docs = await res.json();
        catalogDocumentsCache = Array.isArray(docs) ? docs : [];
        renderCatalogTable(catalogDocumentsCache);
        updateCatalogBadge(catalogDocumentsCache.length, catalogDocumentsCache.length);
    } catch (err) { console.error("Error searching catalog:", err); }
}

async function requestAccess(docId) {
    const email = localStorage.getItem('user_email');
    try {
        const res = await authFetch(`${API_BASE}/requests/${docId}/request?user_email=${encodeURIComponent(email)}`, {
            method: 'POST'
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);

        showAlert(data.message, 'success');
        loadCatalog();
        loadMyRequests();
    } catch (err) {
        showAlert(err.message, 'error');
    }
}

async function loadMyRequests() {
    const email = localStorage.getItem('user_email');
    const status = document.getElementById('requestStatusFilter')?.value || 'ALL';
    const tbody = document.getElementById('myRequestsTableBody');
    if (!tbody) return;

    try {
        let url = `${API_BASE}/requests/my-requests?user_email=${encodeURIComponent(email)}`;
        if (status !== 'ALL') url += `&status_filter=${encodeURIComponent(status)}`;

        const res = await authFetch(url);
        const reqs = await res.json();

        if (!reqs || reqs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No requests found.</td></tr>`;
            return;
        }

        tbody.innerHTML = reqs.map(r => `
            <tr>
                <td><strong>#${r.request_id}</strong></td>
                <td>${r.filename} (ID: #${r.document_id})</td>
                <td>${r.owner_email}</td>
                <td><span class="badge ${r.status.toLowerCase()}">${r.status}</span></td>
                <td>${new Date(r.created_at).toLocaleString()}</td>
            </tr>
        `).join('');
    } catch (err) { console.error(err); }
}

// INCOMING REQUESTS (Dashboard Owner Review)
async function loadDashboardIncomingRequests() {
    const tbody = document.getElementById('dashboardIncomingBody');
    if (!tbody) return;
    const email = localStorage.getItem('user_email');

    try {
        const res = await authFetch(`${API_BASE}/documents/incoming-requests?email=${encodeURIComponent(email)}`);
        const reqs = await res.json();

        if (!reqs || reqs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No incoming requests for your documents.</td></tr>`;
            return;
        }

        tbody.innerHTML = reqs.map(r => {
            const isProcessed = r.status === 'APPROVED' || r.status === 'REJECTED';
            let actions = '';
            if (r.status === 'APPROVED') {
                actions = `<button onclick="revokeAccess(${r.document_id}, '${r.user_email}')" class="danger" style="padding: 4px 8px; font-size: 0.8rem; width: auto !important;">Revoke Access</button>`;
            } else if (r.status === 'PENDING') {
                actions = `
                    <button onclick="manageRequest(${r.id}, 'APPROVED')" style="padding: 4px 8px; background: #22c55e; font-size: 0.8rem; width: auto !important;">Approve</button>
                    <button onclick="manageRequest(${r.id}, 'REJECTED')" class="danger" style="padding: 4px 8px; font-size: 0.8rem; width: auto !important;">Reject</button>
                `;
            } else {
                actions = `<span style="color: var(--text-muted); font-size: 0.85rem;">Status: ${r.status}</span>`;
            }

            return `
                <tr>
                    <td><strong>#${r.id}</strong></td>
                    <td>${r.filename} (ID: #${r.document_id})</td>
                    <td><strong>${r.user_email}</strong></td>
                    <td><span class="badge ${r.status.toLowerCase()}">${r.status}</span></td>
                    <td>${new Date(r.created_at).toLocaleString()}</td>
                    <td>${actions}</td>
                </tr>
            `;
        }).join('');
    } catch (err) { console.error(err); }
}

// INCOMING REQUESTS (Admin Panel View)
async function loadIncomingRequests() {
    const tbody = document.getElementById('incomingRequestsBody');
    if (!tbody) return;
    const email = localStorage.getItem('user_email');

    try {
        const res = await authFetch(`${API_BASE}/documents/incoming-requests?email=${encodeURIComponent(email)}`);
        const reqs = await res.json();

        if (!reqs || reqs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No incoming requests found.</td></tr>`;
            return;
        }

        tbody.innerHTML = reqs.map(r => {
            let actions = '';
            if (r.status === 'APPROVED') {
                actions = `<button onclick="revokeAccess(${r.document_id}, '${r.user_email}')" class="danger" style="padding: 4px 8px; font-size: 0.8rem; width: auto !important;">Revoke Access</button>`;
            } else if (r.status === 'PENDING') {
                actions = `
                    <button onclick="manageRequest(${r.id}, 'APPROVED')" style="padding: 4px 8px; background: #22c55e; font-size: 0.8rem; width: auto !important;">Approve</button>
                    <button onclick="manageRequest(${r.id}, 'REJECTED')" class="danger" style="padding: 4px 8px; font-size: 0.8rem; width: auto !important;">Reject</button>
                `;
            } else {
                actions = `<span style="color: var(--text-muted); font-size: 0.85rem;">Status: ${r.status}</span>`;
            }

            return `
                <tr>
                    <td><strong>#${r.id}</strong></td>
                    <td>${r.filename} (ID: #${r.document_id})</td>
                    <td>${r.user_email}</td>
                    <td>${r.owner_email}</td>
                    <td><span class="badge ${r.status.toLowerCase()}">${r.status}</span></td>
                    <td>${actions}</td>
                </tr>
            `;
        }).join('');
    } catch (err) { console.error(err); }
}

async function manageRequest(requestId, status) {
    const email = localStorage.getItem('user_email');
    try {
        const res = await authFetch(`${API_BASE}/requests/manage/${requestId}?reviewer_email=${encodeURIComponent(email)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: status, actor_email: email })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);

        showAlert(data.message, 'success');
        loadDashboardIncomingRequests();
        loadIncomingRequests();
    } catch (err) {
        showAlert(err.message, 'error');
    }
}

async function revokeAccess(docId, targetEmail) {
    const email = localStorage.getItem('user_email');
    showAppModal({
        title: "Revoke Document Access",
        message: `Revoke read access for user '${targetEmail}' on Document ID #${docId}?`,
        okText: "Revoke Access",
        cancelText: "Cancel",
        onOk: async () => {
            try {
                const res = await authFetch(`${API_BASE}/requests/revoke/${docId}/${encodeURIComponent(targetEmail)}?reviewer_email=${encodeURIComponent(email)}`, {
                    method: 'DELETE'
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail);

                showAlert(data.message, 'success');
                loadDashboardIncomingRequests();
                loadIncomingRequests();
            } catch (err) {
                showAlert(err.message, 'error');
            }
        }
    });
}

// --- PERSONAL VAULT FUNCTIONS ---
let personalDocumentsCache = [];

function renderPersonalTable(docs) {
    const tbody = document.getElementById('personalTableBody');
    if (!tbody) return;
    if (!docs || docs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No personal documents found.</td></tr>`;
        return;
    }
    tbody.innerHTML = docs.map(doc => `
        <tr>
            <td><strong>#${doc.id}</strong></td>
            <td>${doc.filename}</td>
            <td>${new Date(doc.created_at).toLocaleString()}</td>
            <td>
                <button onclick="viewDoc(${doc.id})" class="btn-secondary" style="padding: 4px 8px; width: auto !important;">View</button>
                <button onclick="deletePersonalDocument(${doc.id})" class="danger" style="padding: 4px 8px; width: auto !important;">Delete</button>
            </td>
        </tr>
    `).join('');
}

function filterPersonalDocuments() {
    const query = (document.getElementById('personalSearchInput')?.value || '').toLowerCase().trim();
    if (!query) {
        renderPersonalTable(personalDocumentsCache);
        return;
    }
    const filtered = personalDocumentsCache.filter(doc => 
        doc.id.toString().includes(query) ||
        (doc.filename && doc.filename.toLowerCase().includes(query))
    );
    renderPersonalTable(filtered);
}

function clearPersonalSearch() {
    const input = document.getElementById('personalSearchInput');
    if (input) input.value = '';
    renderPersonalTable(personalDocumentsCache);
}

async function loadPersonalDocuments() {
    const email = localStorage.getItem('user_email');
    const tbody = document.getElementById('personalTableBody');
    if (!tbody) return;

    try {
        const res = await authFetch(`${API_BASE}/documents/personal?user_email=${encodeURIComponent(email)}`);
        const docs = await res.json();
        personalDocumentsCache = Array.isArray(docs) ? docs : [];
        renderPersonalTable(personalDocumentsCache);
    } catch (err) { console.error("Error loading personal documents:", err); }
}

async function uploadPersonalDocument() {
    const fileInput = document.getElementById('uploadPersonalFile');
    const email = localStorage.getItem('user_email');

    if (fileInput.files.length === 0) {
        showAlert("Please select a file to upload.", "error");
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('user_email', email);

    try {
        const res = await authFetch(`${API_BASE}/documents/personal/upload`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);

        showAlert(data.message, 'success');
        fileInput.value = '';
        loadPersonalDocuments();
    } catch (err) {
        showAlert(err.message, 'error');
    }
}

async function deletePersonalDocument(id) {
    showAppModal({
        title: "Delete Private File",
        message: `Permanently delete private document #${id} from your personal vault?`,
        okText: "Delete",
        cancelText: "Cancel",
        onOk: async () => {
            const email = localStorage.getItem('user_email');
            try {
                const res = await authFetch(`${API_BASE}/documents/personal/${id}?user_email=${encodeURIComponent(email)}`, {
                    method: 'DELETE'
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail);

                showAlert(data.message, 'success');
                loadPersonalDocuments();
            } catch (err) {
                showAlert(err.message, 'error');
            }
        }
    });
}
