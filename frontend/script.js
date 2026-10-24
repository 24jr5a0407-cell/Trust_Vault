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
    setTimeout(() => { box.className = ""; box.innerText = ""; }, 4000);
}

// --- AUTH TABS ---
function switchTab(tab) {
    document.getElementById('formLogin').style.display = tab === 'login' ? 'block' : 'none';
    document.getElementById('formRegister').style.display = tab === 'register' ? 'block' : 'none';
    document.getElementById('formRequest').style.display = tab === 'request' ? 'block' : 'none';

    document.getElementById('tabLogin').style.borderBottom = tab === 'login' ? '2px solid var(--primary)' : 'none';
    document.getElementById('tabRegister').style.borderBottom = tab === 'register' ? '2px solid var(--primary)' : 'none';
    document.getElementById('tabRequest').style.borderBottom = tab === 'request' ? '2px solid var(--primary)' : 'none';
}

// --- LOGIN ---
async function handleLogin() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const res = await authFetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
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
    const email = document.getElementById('regEmail').value;
    const secure_code = document.getElementById('regCode').value;
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
    const email = document.getElementById('reqEmail').value;

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

function logout() {
    localStorage.clear();
    window.location.href = 'index.html';
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

    loadUserDocuments();
    loadCatalog();
    loadMyRequests();
    loadDashboardIncomingRequests();
}

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
                <button onclick="viewDoc(${doc.id})" class="btn-secondary" style="padding: 5px 10px; font-size: 0.8rem;">View</button>
                <button onclick="downloadDoc(${doc.id})" style="padding: 5px 10px; font-size: 0.8rem;">Download</button>
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
        alert("Please select a file to upload.");
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

// async function viewDoc(id) {
//     const email = localStorage.getItem('user_email');
//     const token = localStorage.getItem('jwt_token') || '';
    const previewUrl = `${API_BASE}/documents/${id}/preview?user_email=${encodeURIComponent(email)}&token=${encodeURIComponent(token)}`;
    
//     document.getElementById('previewTitle').innerText = `Document Preview (ID: ${id})`;
//     document.getElementById('previewFrame').src = previewUrl;
//     document.getElementById('previewModal').style.display = 'flex';
// }

// function closePreview() {
//     document.getElementById('previewModal').style.display = 'none';
//     document.getElementById('previewFrame').src = '';
// }


// async function viewDoc(id) {
//     const email = localStorage.getItem('user_email');
    
//     // #toolbar=0&navpanes=0&scrollbar=0 hides the top PDF toolbar and side panels
//     const previewUrl = `${API_BASE}/documents/${id}/preview?user_email=${encodeURIComponent(email)}#toolbar=0&navpanes=0&scrollbar=0`;
    
//     document.getElementById('previewTitle').innerText = `Secure Document Viewer (ID: ${id}) - Read Only`;
    
//     const previewObj = document.getElementById('previewObject');
//     previewObj.data = previewUrl;
    
//     document.getElementById('previewModal').style.display = 'flex';
// }


// // Security: Block Right-Click Context Menu & Save/Print Shortcuts inside Preview
// document.addEventListener('DOMContentLoaded', () => {
//     const modal = document.getElementById('previewModal');
//     if (modal) {
//         // Disable right-click
//         modal.addEventListener('contextmenu', (e) => e.preventDefault());
        
//         // Disable hotkeys (Ctrl+S, Ctrl+P)
//         document.addEventListener('keydown', (e) => {
//             if (modal.style.display === 'flex') {
//                 if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'p' || e.key === 'S' || e.key === 'P')) {
//                     e.preventDefault();
//                     alert("Downloading, saving, and printing are disabled for security reasons.");
//                 }
//             }
//         });
//     }
// });

// function closePreview() {
//     document.getElementById('previewModal').style.display = 'none';
//     document.getElementById('previewObject').data = '';
// }


// Configure PDF.js worker source
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

// --- SECURE CANVAS DOCUMENT VIEWER ---
async function viewDoc(id) {
    const email = localStorage.getItem('user_email');
    const token = localStorage.getItem('jwt_token') || '';
    const previewUrl = `${API_BASE}/documents/${id}/preview?user_email=${encodeURIComponent(email)}&token=${encodeURIComponent(token)}`;
    
    document.getElementById('previewTitle').innerText = `Secure Document Viewer (ID: ${id}) - Read Only`;
    document.getElementById('previewModal').style.display = 'flex';
    
    const container = document.getElementById('pdfViewerContainer');
    container.innerHTML = '<p style="color: white; margin-top: 50px;">Loading secure document...</p>';

    try {
        // Load the PDF from your FastAPI backend endpoint
        const loadingTask = pdfjsLib.getDocument(previewUrl);
        const pdfDoc = await loadingTask.promise;
        
        container.innerHTML = ''; // Clear loading message

        // Loop through each page of the document and draw it onto a canvas
        for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
            const page = await pdfDoc.getPage(pageNum);
            const scale = 1.5; // Zoom scale for clear readability
            const viewport = page.getViewport({ scale: scale });

            // Create an HTML5 canvas for the page
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.height = viewport.height;
            canvas.width = viewport.width;
            canvas.style.boxShadow = '0 4px 6px rgba(0,0,0,0.3)';
            canvas.style.marginBottom = '10px';
            canvas.style.backgroundColor = 'white';

            container.appendChild(canvas);

            // Render PDF page into canvas context
            const renderContext = {
                canvasContext: context,
                viewport: viewport
            };
            await page.render(renderContext).promise;
        }
    } catch (err) {
        container.innerHTML = `<p style="color: #f87171; margin-top: 50px;">Failed to load secure document preview: ${err.message}</p>`;
    }
}

function closePreview() {
    document.getElementById('previewModal').style.display = 'none';
    document.getElementById('pdfViewerContainer').innerHTML = '';
}

async function downloadDoc(id) {
    const email = localStorage.getItem('user_email');
    const token = localStorage.getItem('jwt_token') || '';
    window.location.href = `${API_BASE}/documents/${id}/download?user_email=${encodeURIComponent(email)}&token=${encodeURIComponent(token)}`;
}

async function editDoc(id, currentName) {
    const newName = prompt("Enter new filename:", currentName);
    if (!newName) return;

    const email = localStorage.getItem('user_email');
    try {
        const res = await authFetch(`${API_BASE}/documents/${id}?user_email=${encodeURIComponent(email)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: newName })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);

        showAlert("Document updated successfully!", "success");
        loadUserDocuments();
    } catch (err) {
        alert(err.message);
    }
}

async function shareDoc(id) {
    const targetEmail = prompt("Enter the approved user's email to grant read-only access:");
    if (!targetEmail) return;

    try {
        const res = await authFetch(`${API_BASE}/documents/${id}/grant`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_email: targetEmail })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        alert(data.message);
    } catch (err) {
        alert(err.message);
    }
}

async function deleteDoc(id) {
    if (!confirm("Are you sure you want to delete this document permanently?")) return;

    const email = localStorage.getItem('user_email');
    try {
        const res = await authFetch(`${API_BASE}/documents/${id}?user_email=${encodeURIComponent(email)}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);

        showAlert("Document deleted successfully!", "success");
        loadUserDocuments();
    } catch (err) {
        alert(err.message);
    }
}


// --- ADMIN PANEL FUNCTIONS ---
async function checkAdminAuthAndLoad() {
    const isAdmin = localStorage.getItem('is_admin') === 'true';
    if (!isAdmin) {
        alert("Access denied. Admin privileges required.");
        window.location.href = 'dashboard.html';
        return;
    }
    loadAdminRequests();
    loadAdminUsers();
    loadAdminDocuments();
    loadAdminLedger();
    loadIncomingRequests();
}

// Admin Requests Table Rendering (Disables / hides admin actions)
async function loadAdminRequests() {
    const tbody = document.getElementById('requestsTableBody');
    try {
        const res = await authFetch(`${API_BASE}/admin/requests`);
        const reqs = await res.json();

        tbody.innerHTML = reqs.map(r => {
            const isAdmin = r.email === 'admin@trustvault.com';
            const isProcessed = r.status === 'APPROVED' || r.status === 'REJECTED';

            let actionHtml = '';
            if (isAdmin) {
                actionHtml = '<span style="color: var(--text-muted); font-size: 0.85rem;">System Admin</span>';
            } else if (isProcessed) {
                actionHtml = `<span style="color: var(--text-muted); font-size: 0.85rem;">Completed (${r.status})</span>`;
            } else {
                actionHtml = `
                    <button onclick="updateRequestStatus('${r.email}', 'APPROVED')" style="padding: 4px 8px; background: #22c55e;">Approve</button>
                    <button onclick="updateRequestStatus('${r.email}', 'REJECTED')" class="danger" style="padding: 4px 8px;">Reject</button>
                `;
            }

            return `
                <tr>
                    <td>${r.id}</td>
                    <td>${r.email}</td>
                    <td><span class="badge ${r.status.toLowerCase()}">${r.status}</span></td>
                    <td>${r.secure_code || 'N/A'}</td>
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
        alert(err.message);
    }
}

async function loadAdminUsers() {
    const tbody = document.getElementById('usersTableBody');
    try {
        const res = await authFetch(`${API_BASE}/admin/users`);
        const users = await res.json();

        tbody.innerHTML = users.map(u => `
            <tr>
                <td>${u.id}</td>
                <td>${u.email}</td>
                <td>${u.is_admin ? 'Yes' : 'No'}</td>
                <td>${new Date(u.created_at).toLocaleString()}</td>
                <td>
                    ${u.email !== 'admin@trustvault.com' ? `<button onclick="removeUser('${u.email}')" class="danger" style="padding: 4px 8px; font-size: 0.8rem;">Remove User</button>` : 'Primary Admin'}
                </td>
            </tr>
        `).join('');
    } catch (err) { console.error(err); }
}

async function removeUser(email) {
    if (!confirm(`Are you sure you want to remove user ${email}? Their documents will be reassigned to admin.`)) return;

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
        alert(err.message);
    }
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

        if (logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;">No audit logs found.</td></tr>`;
            return;
        }

        tbody.innerHTML = logs.map(l => `
            <tr>
                <td>${l.id}</td>
                <td>${l.filename} (ID: ${l.document_id})</td>
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


// --- CATALOG & REQUEST FUNCTIONS ---
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
    // Instant client-side file-manager filter (ID, full name, or half-name substring)
    const filtered = catalogDocumentsCache.filter(doc => 
        doc.id.toString().includes(query) ||
        (doc.filename && doc.filename.toLowerCase().includes(query)) ||
        (doc.owner_email && doc.owner_email.toLowerCase().includes(query))
    );
    renderCatalogTable(filtered);
    updateCatalogBadge(filtered.length, catalogDocumentsCache.length);

    // Debounced server-side query for full database synchronization
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

async function loadCatalog() {
    const email = localStorage.getItem('user_email');
    const tbody = document.getElementById('catalogTableBody');
    if (!tbody) return;

    try {
        const res = await authFetch(`${API_BASE}/documents/catalog?user_email=${encodeURIComponent(email)}`);
        const docs = await res.json();
        catalogDocumentsCache = Array.isArray(docs) ? docs : [];
        renderCatalogTable(catalogDocumentsCache);
        updateCatalogBadge(catalogDocumentsCache.length, catalogDocumentsCache.length);
    } catch (err) { console.error("Error loading catalog:", err); }
}

async function searchCatalog() {
    const email = localStorage.getItem('user_email');
    const query = (document.getElementById('searchInput')?.value || '').trim();
    const tbody = document.getElementById('catalogTableBody');
    if (!tbody) return;

    try {
        const url = query 
            ? `${API_BASE}/documents/catalog?user_email=${encodeURIComponent(email)}&search=${encodeURIComponent(query)}`
            : `${API_BASE}/documents/catalog?user_email=${encodeURIComponent(email)}`;
        const res = await authFetch(url);
        const docs = await res.json();
        const results = Array.isArray(docs) ? docs : [];
        renderCatalogTable(results);
        updateCatalogBadge(results.length, catalogDocumentsCache.length || results.length);
    } catch (err) { console.error("Error searching catalog:", err); }
}


function renderCatalogTable(docs) {
    const tbody = document.getElementById('catalogTableBody');
    if (docs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;">No documents found.</td></tr>`;
        return;
    }

    tbody.innerHTML = docs.map(doc => {
        let actionBtn = '';
        let statusBadge = '';

        if (doc.is_owner) {
            statusBadge = `<span class="badge approved">Owner</span>`;
            actionBtn = `<button onclick="viewDoc(${doc.id})" class="btn-secondary" style="padding: 4px 8px;">View</button>`;
        } else if (doc.has_access) {
            statusBadge = `<span class="badge approved">Access Granted</span>`;
            // Regular users with access ONLY get to view. No revoke button here!
            actionBtn = `
                <button onclick="viewDoc(${doc.id})" class="btn-secondary" style="padding: 4px 8px;">View (Read-Only)</button>
            `;
        } else if (doc.request_status === 'PENDING') {
            statusBadge = `<span class="badge pending">Pending Approval</span>`;
            actionBtn = `<button disabled style="background: #94a3b8; padding: 4px 8px;">Requested</button>`;
        } else if (doc.request_status === 'APPROVED') {
            statusBadge = `<span class="badge approved">Approved</span>`;
            actionBtn = `<button onclick="viewDoc(${doc.id})" class="btn-secondary" style="padding: 4px 8px;">View</button>`;
        } else {
            statusBadge = `<span class="badge rejected">${doc.request_status}</span>`;
            actionBtn = `<button onclick="requestDocAccess(${doc.id})" style="padding: 4px 8px; background: #0d9488;">Request Access</button>`;
        }

        return `
            <tr>
                <td>${doc.id}</td>
                <td>${doc.filename}</td>
                <td>${doc.owner_email}</td>
                <td>${statusBadge}</td>
                <td>${actionBtn}</td>
            </tr>
        `;
    }).join('');
}
// function renderCatalogTable(docs) {
//     const tbody = document.getElementById('catalogTableBody');
//     if (docs.length === 0) {
//         tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;">No documents found.</td></tr>`;
//         return;
//     }

//     tbody.innerHTML = docs.map(doc => {
//         let actionBtn = '';
//         let statusBadge = '';

//         if (doc.is_owner) {
//             statusBadge = `<span class="badge approved">Owner</span>`;
//             actionBtn = `<button onclick="viewDoc(${doc.id})" class="btn-secondary" style="padding: 4px 8px;">View</button>`;
//         } else if (doc.has_access) {
//             statusBadge = `<span class="badge approved">Access Granted</span>`;
//             actionBtn = `
//                 <button onclick="viewDoc(${doc.id})" class="btn-secondary" style="padding: 4px 8px;">View (Read-Only)</button>
//                 <button onclick="revokeAccess(${doc.id}, '${localStorage.getItem('user_email')}')" class="danger" style="padding: 4px 8px;">Revoke</button>
//             `;
//         } else if (doc.request_status === 'PENDING') {
//             statusBadge = `<span class="badge pending">Pending Approval</span>`;
//             actionBtn = `<button disabled style="background: #94a3b8; padding: 4px 8px;">Requested</button>`;
//         } else if (doc.request_status === 'APPROVED') {
//             statusBadge = `<span class="badge approved">Approved</span>`;
//             actionBtn = `<button onclick="viewDoc(${doc.id})" class="btn-secondary" style="padding: 4px 8px;">View</button>`;
//         } else {
//             statusBadge = `<span class="badge rejected">${doc.request_status}</span>`;
//             actionBtn = `<button onclick="requestDocAccess(${doc.id})" style="padding: 4px 8px; background: #0d9488;">Request Access</button>`;
//         }

//         return `
//             <tr>
//                 <td>${doc.id}</td>
//                 <td>${doc.filename}</td>
//                 <td>${doc.owner_email}</td>
//                 <td>${statusBadge}</td>
//                 <td>${actionBtn}</td>
//             </tr>
//         `;
//     }).join('');
// }

async function requestDocAccess(documentId) {
    const email = localStorage.getItem('user_email');
    try {
        const res = await authFetch(`${API_BASE}/documents/${documentId}/request-access?user_email=${encodeURIComponent(email)}`, {
            method: 'POST'
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);

        showAlert(data.message, 'success');
        loadCatalog();
        loadMyRequests();
    } catch (err) {
        alert(err.message);
    }
}

async function loadMyRequests() {
    const email = localStorage.getItem('user_email');
    const statusFilter = document.getElementById('requestStatusFilter')?.value || 'ALL';
    const tbody = document.getElementById('myRequestsTableBody');
    if (!tbody) return;

    try {
        const res = await authFetch(`${API_BASE}/documents/my-requests?user_email=${encodeURIComponent(email)}&status=${statusFilter}`);
        const reqs = await res.json();

        if (reqs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;">No requests found.</td></tr>`;
            return;
        }

        tbody.innerHTML = reqs.map(r => `
            <tr>
                <td>${r.id}</td>
                <td>${r.filename} (ID: ${r.document_id})</td>
                <td>${r.owner_email}</td>
                <td><span class="badge ${r.status.toLowerCase()}">${r.status}</span></td>
                <td>${new Date(r.created_at).toLocaleString()}</td>
            </tr>
        `).join('');
    } catch (err) { console.error(err); }
}

// --- INCOMING REQUESTS QUEUE FOR OWNERS & ADMINS ---
async function loadIncomingRequests() {
    const email = localStorage.getItem('user_email');
    const tbody = document.getElementById('incomingRequestsBody');
    if (!tbody) return;

    try {
        const res = await authFetch(`${API_BASE}/documents/incoming-requests?email=${encodeURIComponent(email)}`);
        const reqs = await res.json();

        if (reqs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center;">No incoming requests.</td></tr>`;
            return;
        }

        tbody.innerHTML = reqs.map(r => `
            <tr>
                <td>${r.id}</td>
                <td>ID: ${r.document_id} - ${r.filename}</td>
                <td>${r.user_email}</td>
                <td>${r.owner_email}</td>
                <td><span class="badge ${r.status.toLowerCase()}">${r.status}</span></td>
                <td>
                    ${r.status === 'PENDING' ? `
                        <button onclick="manageRequest(${r.id}, 'APPROVED')" style="padding: 4px 8px; background: #22c55e;">Approve</button>
                        <button onclick="manageRequest(${r.id}, 'REJECTED')" class="danger" style="padding: 4px 8px;">Reject</button>
                    ` : (r.status === 'APPROVED' ? `
                        <button onclick="manageRequest(${r.id}, 'REVOKED')" class="danger" style="padding: 4px 8px;">Revoke Access</button>
                    ` : `<span>Completed</span>`)}
                </td>
            </tr>
        `).join('');
    } catch (err) { console.error(err); }
}

async function manageRequest(requestId, status) {
    const email = localStorage.getItem('user_email');
    try {
        const res = await authFetch(`${API_BASE}/documents/requests/${requestId}/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: status, actor_email: email })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);

        showAlert(data.message, 'success');
        loadIncomingRequests();
    } catch (err) {
        alert(err.message);
    }
}


// --- TAB SWITCHING ---
function switchDashboardTab(tab) {
    document.getElementById('sectionVault').style.display = tab === 'vault' ? 'block' : 'none';
    document.getElementById('sectionCatalog').style.display = tab === 'catalog' ? 'block' : 'none';
    document.getElementById('sectionIncoming').style.display = tab === 'incoming' ? 'block' : 'none';

    document.getElementById('tabVault').style.background = tab === 'vault' ? 'var(--primary)' : '#64748b';
    document.getElementById('tabCatalog').style.background = tab === 'catalog' ? 'var(--primary)' : '#64748b';
    document.getElementById('tabIncoming').style.background = tab === 'incoming' ? 'var(--primary)' : '#64748b';
}



// --- INCOMING REQUESTS FOR OWNERS ---
async function loadDashboardIncomingRequests() {
    const email = localStorage.getItem('user_email');
    const tbody = document.getElementById('dashboardIncomingBody');
    if (!tbody) return;

    try {
        const res = await authFetch(`${API_BASE}/documents/incoming-requests?email=${encodeURIComponent(email)}`);
        const reqs = await res.json();

        if (reqs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No incoming requests for your documents.</td></tr>`;
            return;
        }

        tbody.innerHTML = reqs.map(r => `
            <tr>
                <td>${r.id}</td>
                <td>ID: ${r.document_id} - ${r.filename}</td>
                <td>${r.user_email}</td>
                <td><span class="badge ${r.status.toLowerCase()}">${r.status}</span></td>
                <td>${new Date(r.created_at).toLocaleString()}</td>
                <td>
                    ${r.status === 'PENDING' ? `
                        <button onclick="manageDashboardRequest(${r.id}, 'APPROVED')" style="padding: 4px 8px; background: #22c55e;">Approve</button>
                        <button onclick="manageDashboardRequest(${r.id}, 'REJECTED')" class="danger" style="padding: 4px 8px;">Reject</button>
                    ` : (r.status === 'APPROVED' ? `
                        <button onclick="manageDashboardRequest(${r.id}, 'REVOKED')" class="danger" style="padding: 4px 8px;">Revoke Access</button>
                    ` : `<span style="color: var(--text-muted);">Completed</span>`)}
                </td>
            </tr>
        `).join('');
    } catch (err) { console.error(err); }
}

async function manageDashboardRequest(requestId, status) {
    const email = localStorage.getItem('user_email');
    try {
        const res = await authFetch(`${API_BASE}/documents/requests/${requestId}/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: status, actor_email: email })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);

        showAlert(data.message, 'success');
        loadDashboardIncomingRequests();
        loadCatalog();
    } catch (err) {
        alert(err.message);
    }
}

// --- TAB SWITCHING ---
function switchDashboardTab(tab) {
    document.getElementById('sectionVault').style.display = tab === 'vault' ? 'block' : 'none';
    document.getElementById('sectionCatalog').style.display = tab === 'catalog' ? 'block' : 'none';
    document.getElementById('sectionIncoming').style.display = tab === 'incoming' ? 'block' : 'none';
    document.getElementById('sectionPersonal').style.display = tab === 'personal' ? 'block' : 'none';

    document.getElementById('tabVault').style.background = tab === 'vault' ? 'var(--primary)' : '#64748b';
    document.getElementById('tabCatalog').style.background = tab === 'catalog' ? 'var(--primary)' : '#64748b';
    document.getElementById('tabIncoming').style.background = tab === 'incoming' ? 'var(--primary)' : '#64748b';
    document.getElementById('tabPersonal').style.background = tab === 'personal' ? 'var(--primary)' : '#64748b';
}

// --- INITIALIZATION ---
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

    loadUserDocuments();
    loadCatalog();
    loadMyRequests();
    loadDashboardIncomingRequests();
    loadPersonalDocuments(); // Load private personal vault
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
                <button onclick="viewDoc(${doc.id})" class="btn-secondary" style="padding: 4px 8px;">View</button>
                <button onclick="deletePersonalDocument(${doc.id})" class="danger" style="padding: 4px 8px;">Delete</button>
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
        alert("Please select a file to upload.");
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
        alert(err.message);
    }
}

async function deletePersonalDocument(id) {
    if (!confirm(`Are you sure you want to delete personal document ID ${id}?`)) return;
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
        alert(err.message);
    }
}