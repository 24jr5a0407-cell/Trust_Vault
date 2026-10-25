// ============================================================================
// Trust Vault — Common Primitives & Security Utilities
// ============================================================================

// Dynamic Production & Localhost API Base Resolution
const API_BASE = (window.location.origin && !window.location.origin.startsWith('file:') && !window.location.origin.includes(':8000'))
    ? `${window.location.origin}/api`
    : 'http://127.0.0.1:8000/api';

/**
 * Wrapper for fetch API automatically attaching Bearer JWT tokens from localStorage.
 */
function authFetch(url, options = {}) {
    const token = localStorage.getItem('jwt_token');
    const headers = options.headers ? { ...options.headers } : {};
    if (token && !headers['Authorization']) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return fetch(url, { ...options, headers });
}

/**
 * Displays floating notification banner (success, error, warning).
 */
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

    const titleEl = document.getElementById('appModalTitle');
    const msgEl = document.getElementById('appModalMessage');
    const btnContainer = document.getElementById('appModalButtons');

    if (titleEl) titleEl.innerText = title;
    if (msgEl) msgEl.innerText = message;
    if (btnContainer) {
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
    }

    modal.style.display = 'flex';
}

function closeAppModal() {
    const modal = document.getElementById('appModal');
    if (modal) modal.style.display = 'none';
}

// Requirement: Professional warning when direct download is attempted
function showDownloadDisabledWarning() {
    showAppModal({
        title: "🛡️ Direct Download Prohibited",
        message: "Trust Vault Enterprise Security Policy prohibits direct file downloading to prevent unauthorized data exfiltration. All documents are restricted to secure, in-browser cryptographic read-only inspection."
    });
}

// Session Termination / Logout with Modal Confirmation
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


/**
 * Formats ISO or UTC timestamps accurately into the user's local timezone.
 * Appends 'Z' to UTC SQLite strings like 'YYYY-MM-DD HH:MM:SS' if missing.
 */
function formatLocalDate(dateStr) {
    if (!dateStr) return '—';
    try {
        let clean = String(dateStr).trim();
        // If string lacks timezone indicator ('Z' or offset), treat SQLite default as UTC
        if (!clean.includes('Z') && !clean.includes('+') && !clean.includes('T')) {
            clean = clean.replace(' ', 'T') + 'Z';
        } else if (clean.includes('T') && !clean.endsWith('Z') && !clean.includes('+')) {
            clean += 'Z';
        }
        const d = new Date(clean);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleString(undefined, {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        });
    } catch (e) {
        return dateStr;
    }
}
