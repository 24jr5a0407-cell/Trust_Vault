// ============================================================================
// Trust Vault — User Dashboard Controller
// Handles Accessible Documents, Catalog Search, Access Requests, and Personal Vault
// ============================================================================

// --- INITIALIZATION & AUTH GUARD ---
async function checkAuthAndLoadDashboard() {
    const email = localStorage.getItem('user_email');
    const isAdmin = localStorage.getItem('is_admin') === 'true';

    if (!email) {
        window.location.href = 'index.html';
        return;
    }

    const welcomeEl = document.getElementById('userWelcome');
    const adminNavBtn = document.getElementById('adminNavBtn');

    if (welcomeEl) welcomeEl.innerText = `Logged in as: ${email}`;
    if (isAdmin && adminNavBtn) {
        adminNavBtn.style.display = 'inline-block';
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

// --- TAB NAVIGATION ---
function switchDashboardTab(tab) {
    const sections = ['vault', 'catalog', 'incoming', 'personal', 'profile'];
    sections.forEach(s => {
        const secEl = document.getElementById(`section${s.charAt(0).toUpperCase() + s.slice(1)}`);
        const tabBtn = document.getElementById(`tab${s.charAt(0).toUpperCase() + s.slice(1)}`);
        if (secEl) secEl.style.display = (tab === s) ? 'block' : 'none';
        if (tabBtn) {
            if (tab === s) {
                tabBtn.classList.add('tab-active');
                tabBtn.style.background = '#ffffff';
                tabBtn.style.color = '#0f172a';
            } else {
                tabBtn.classList.remove('tab-active');
                tabBtn.style.background = 'transparent';
                tabBtn.style.color = '#64748b';
            }
        }
    });

    if (tab === 'profile') {
        loadUserProfile();
    }
}

// --- 1. MY VAULT (ACCESSIBLE DOCUMENTS) ---
let userVaultDocumentsCache = [];

function renderVaultTable(docs) {
    const tbody = document.getElementById('documentTableBody');
    if (!tbody) return;
    if (!docs || docs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No accessible documents found. You have not uploaded any files, and no owner has granted you view permissions yet.</td></tr>`;
        return;
    }

    const currentEmail = (localStorage.getItem('user_email') || '').toLowerCase().trim();

    tbody.innerHTML = docs.map(doc => {
        const isOwner = (doc.owner_email || '').toLowerCase().trim() === currentEmail;
        
        let roleBadge = '';
        let downloadBtn = '';

        if (isOwner) {
            roleBadge = `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 12px; font-size: 0.76rem; font-weight: 700; background: #e0e7ff; color: #4338ca;">👑 Document Owner</span>`;
            downloadBtn = `<button onclick="downloadOfficialDoc(${doc.id})" class="btn-secondary" style="padding: 6px 12px; font-size: 0.82rem; width: auto !important; color: #0284c7 !important; border-color: #bae6fd !important;">⬇️ Download</button>`;
        } else {
            roleBadge = `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 12px; font-size: 0.76rem; font-weight: 700; background: #dcfce7; color: #15803d;">👁️ Granted Viewer</span>`;
            downloadBtn = `<button onclick="showDownloadDisabledWarning()" class="btn-download-vault" style="padding: 6px 12px; font-size: 0.82rem; width: auto !important;">🔒 Download Blocked</button>`;
        }

        return `
            <tr>
                <td><strong>#${doc.id}</strong></td>
                <td>${doc.filename}</td>
                <td>${doc.owner_email}</td>
                <td>${roleBadge}</td>
                <td>${new Date(doc.created_at).toLocaleString()}</td>
                <td>
                    <button onclick="viewDoc(${doc.id})" class="btn-secondary" style="padding: 6px 12px; font-size: 0.82rem; width: auto !important;">👁️ View</button>
                    ${downloadBtn}
                </td>
            </tr>
        `;
    }).join('');
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

    if (!fileInput || fileInput.files.length === 0) {
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

// --- 2. CATALOG & PUBLIC PERMISSION REQUESTS ---
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
                <button onclick="viewDoc(${doc.id})" class="btn-secondary" style="padding: 5px 10px; font-size: 0.82rem; width: auto !important;">👁️ View</button>
                <button onclick="showDownloadDisabledWarning()" class="btn-download-vault" style="padding: 5px 10px; font-size: 0.82rem; width: auto !important;">⬇️ Download</button>
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

// --- 3. INCOMING REQUESTS (DOC OWNER APPROVALS) ---
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
            const currentStatus = r.status.toUpperCase();
            const actionSelect = `
                <select onchange="manageRequest(${r.id}, this.value)" style="height: 32px; padding: 2px 8px; font-size: 0.82rem; border-radius: 6px; border: 1px solid #cbd5e1; background: white; font-weight: 600;">
                    <option value="APPROVED" ${currentStatus === 'APPROVED' ? 'selected' : ''}>✅ Grant Access (Approved)</option>
                    <option value="REJECTED" ${currentStatus === 'REJECTED' ? 'selected' : ''}>❌ Reject Access</option>
                    <option value="REVOKED" ${currentStatus === 'REVOKED' ? 'selected' : ''}>🚫 Revoke Access</option>
                    <option value="PENDING" ${currentStatus === 'PENDING' ? 'selected' : ''}>⏳ Pending</option>
                </select>
            `;

            return `
                <tr>
                    <td><strong>#${r.id}</strong></td>
                    <td>${r.filename} (ID: #${r.document_id})</td>
                    <td><strong>${r.user_email}</strong></td>
                    <td><span class="badge ${r.status.toLowerCase()}">${r.status}</span></td>
                    <td>${new Date(r.created_at).toLocaleString()}</td>
                    <td>${actionSelect}</td>
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
        const incomingTable = document.getElementById('incomingRequestsBody');
        if (incomingTable) loadIncomingRequests();
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
                const incomingTable = document.getElementById('incomingRequestsBody');
                if (incomingTable) loadIncomingRequests();
            } catch (err) {
                showAlert(err.message, 'error');
            }
        }
    });
}

// --- 4. PERSONAL VAULT (ZERO-KNOWLEDGE PRIVATE STORAGE) ---
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

    if (!fileInput || fileInput.files.length === 0) {
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

// --- 5. USER PROFILE CONTROLLER ---
async function loadUserProfile() {
    const email = localStorage.getItem('user_email');
    if (!email) return;

    try {
        const res = await authFetch(`${API_BASE}/profile?user_email=${encodeURIComponent(email)}`);
        const user = await res.json();
        if (!res.ok) throw new Error(user.detail || "Failed to load profile");

        const nameHeader = document.getElementById('profileNameHeader');
        const emailHeader = document.getElementById('profileEmailHeader');
        const roleBadge = document.getElementById('profileRoleBadge');
        const photoDisplay = document.getElementById('profilePhotoDisplay');

        const editName = document.getElementById('editProfileName');
        const editPhone = document.getElementById('editProfilePhone');
        const editGender = document.getElementById('editProfileGender');
        const editEmail = document.getElementById('editProfileEmail');
        const editPhoto = document.getElementById('editProfilePhoto');

        if (nameHeader) nameHeader.innerText = user.full_name || 'My Profile';
        if (emailHeader) emailHeader.innerText = user.email;
        if (roleBadge) {
            roleBadge.innerText = user.is_admin ? "🛡️ System Administrator" : "👤 Verified Vault User";
            roleBadge.className = user.is_admin ? "badge" : "badge approved";
            if (user.is_admin) {
                roleBadge.style.background = "#e0e7ff";
                roleBadge.style.color = "#4338ca";
            }
        }

        if (photoDisplay && user.profile_photo) {
            photoDisplay.src = user.profile_photo;
        }

        if (editName) editName.value = user.full_name || '';
        if (editPhone) editPhone.value = user.phone || '';
        if (editGender) editGender.value = user.gender || '';
        if (editEmail) editEmail.value = user.email;
        if (editPhoto) editPhoto.value = user.profile_photo || '';
    } catch (err) {
        console.error("Failed to load profile:", err);
    }
}

function updateProfilePhotoPreview(url) {
    const photoDisplay = document.getElementById('profilePhotoDisplay');
    if (!photoDisplay) return;
    if (url && url.trim().length > 5) {
        photoDisplay.src = url.trim();
    } else {
        photoDisplay.src = 'logo-icon.png';
    }
}

function handleProfilePhotoSelected(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
        showAlert("Please select a valid image file (PNG, JPG, WebP).", "error");
        return;
    }

    if (file.size > 2 * 1024 * 1024) {
        showAlert("Image size is too large. Please select an image under 2MB.", "error");
        return;
    }

    const reader = new FileReader();
    reader.onload = function(e) {
        const base64Data = e.target.result;
        const photoDisplay = document.getElementById('profilePhotoDisplay');
        const editPhoto = document.getElementById('editProfilePhoto');
        if (photoDisplay) photoDisplay.src = base64Data;
        if (editPhoto) editPhoto.value = base64Data;
        showAlert("Photo loaded! Click 'Save Profile Changes' to update your account.", "info");
    };
    reader.readAsDataURL(file);
}

async function saveUserProfile() {
    const email = localStorage.getItem('user_email');
    if (!email) {
        showAlert("No logged-in user found. Please re-authenticate.", "error");
        return;
    }

    const full_name = (document.getElementById('editProfileName')?.value || '').trim();
    const phone = (document.getElementById('editProfilePhone')?.value || '').trim();
    const gender = (document.getElementById('editProfileGender')?.value || '').trim();
    const profile_photo = (document.getElementById('editProfilePhoto')?.value || '').trim();

    try {
        showAlert("Saving profile changes...", "info");
        const res = await authFetch(`${API_BASE}/profile?user_email=${encodeURIComponent(email)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                full_name: full_name || null, 
                phone: phone || null, 
                gender: gender || null, 
                profile_photo: profile_photo || null 
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to update profile");

        showAlert(data.message || "Profile updated successfully!", "success");
        loadUserProfile();
    } catch (err) {
        showAlert(err.message, "error");
    }
}
