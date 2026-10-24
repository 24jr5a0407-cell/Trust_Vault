// ============================================================================
// Trust Vault — Administrator Governance & Compliance Panel Controller
// Manages User Whitelisting, Active Users, Document Oversight, and Audit Ledger
// ============================================================================

// --- ADMIN AUTH GUARD & INITIALIZATION ---
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

// --- 1. USER ACCOUNT WHITELIST & ONBOARDING ---
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

// --- 2. ACTIVE USER MANAGEMENT ---
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

// --- 3. DOCUMENT OVERSIGHT ---
let adminDocsCache = [];

function renderAdminDocsTable(docs) {
    const tbody = document.getElementById('adminDocsTableBody');
    if (!tbody) return;
    if (!docs || docs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No documents found.</td></tr>`;
        return;
    }
    tbody.innerHTML = docs.map(d => `
        <tr>
            <td><strong>#${d.id}</strong></td>
            <td>${d.filename}</td>
            <td>${d.owner_email}</td>
            <td>${new Date(d.created_at).toLocaleString()}</td>
            <td>
                <button onclick="viewDoc(${d.id})" class="btn-secondary" style="padding: 4px 8px; font-size: 0.8rem; width: auto !important;">View</button>
            </td>
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

// --- 4. IMMUTABLE AUDIT LEDGER & COMPLIANCE CSV EXPORT ---
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

// --- 5. INCOMING ACCESS REQUESTS (ADMIN VIEW) ---
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
                loadIncomingRequests();
            } catch (err) {
                showAlert(err.message, 'error');
            }
        }
    });
}
