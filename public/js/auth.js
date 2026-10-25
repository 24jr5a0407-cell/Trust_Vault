// ============================================================================
// Trust Vault — Authentication, Whitelist Registration & 2FA Lifecycle
// Used primarily on index.html
// ============================================================================

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
        if (err.message && err.message.toLowerCase().includes("account not found")) {
            showAppModal({
                title: "Account Not Found",
                message: "This account was not found in Trust Vault. Please submit an access request to the administrator and register your account.",
                okText: "Request Access Now",
                cancelText: "Register with Code",
                onOk: () => {
                    const reqEmail = document.getElementById('reqEmail');
                    if (reqEmail) reqEmail.value = email;
                    switchTab('request');
                },
                onCancel: () => {
                    const regEmail = document.getElementById('regEmail');
                    if (regEmail) regEmail.value = email;
                    switchTab('register');
                }
            });
        } else {
            showAlert(err.message, 'error');
        }
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

// --- REGISTER (WITH PRE-APPROVED SECURE CODE) ---
async function handleRegister() {
    const email = document.getElementById('regEmail')?.value.trim();
    const full_name = document.getElementById('regFullName')?.value.trim() || '';
    const phone = document.getElementById('regPhone')?.value.trim() || '';
    const gender = document.getElementById('regGender')?.value || '';
    const secure_code = document.getElementById('regCode')?.value.trim();
    const password = document.getElementById('regPassword')?.value;

    try {
        const res = await authFetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, secure_code, password, full_name, phone, gender })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Registration failed");

        showAlert(data.message, 'success');
        switchTab('login');
    } catch (err) {
        showAlert(err.message, 'error');
    }
}

// --- REQUEST ACCESS (SUBMIT EMAIL FOR WHITELISTING) ---
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
