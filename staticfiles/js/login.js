/**
 * Mediculus — Сторінка входу (2-кроковий)
 */
document.addEventListener('DOMContentLoaded', () => {
    if (isAuthenticated()) { redirectByRole(); return; }

    // Show success message after password reset
    const params = new URLSearchParams(window.location.search);
    if (params.get('password_reset') === '1') {
        const err = document.getElementById('login-error');
        err.className = 'alert alert-success';
        document.getElementById('login-error-msg').textContent = 'Пароль успішно змінено. Тепер ви можете увійти.';
        err.classList.remove('d-none');
    }

    setupStep1();
    setupStep2();
    setupTogglePassword();

    // Init Bootstrap tooltip
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });
});

function goToStep2(email) {
    document.getElementById('step-email').classList.add('d-none');
    document.getElementById('step-password').classList.remove('d-none');
    document.getElementById('login-email-display').value = email;
    document.getElementById('login-password').focus();
    document.getElementById('login-error').classList.add('d-none');
}

function goToStep1() {
    document.getElementById('step-password').classList.add('d-none');
    document.getElementById('step-email').classList.remove('d-none');
    document.getElementById('login-password').value = '';
    document.getElementById('login-error').classList.add('d-none');
    document.getElementById('login-email').focus();
}

function setupStep1() {
    const nextBtn = document.getElementById('next-btn');
    const emailInput = document.getElementById('login-email');

    const proceed = () => {
        const email = emailInput?.value.trim();
        if (!email || !email.includes('@')) {
            const err = document.getElementById('login-error');
            err.className = 'alert alert-danger';
            document.getElementById('login-error-msg').textContent = 'Введіть коректний email.';
            err.classList.remove('d-none');
            return;
        }
        goToStep2(email);
    };

    nextBtn?.addEventListener('click', proceed);
    emailInput?.addEventListener('keypress', (e) => { if (e.key === 'Enter') proceed(); });
}

function setupStep2() {
    const loginBtn = document.getElementById('login-btn');
    const changeEmailBtn = document.getElementById('change-email-btn');

    changeEmailBtn?.addEventListener('click', goToStep1);

    const doLogin = async () => {
        const email = document.getElementById('login-email')?.value.trim() ||
                      document.getElementById('login-email-display')?.value.trim();
        const password = document.getElementById('login-password').value;
        const rememberMe = document.getElementById('remember-me')?.checked || false;
        const errorDiv = document.getElementById('login-error');
        const btn = document.getElementById('login-btn');
        const spinner = document.getElementById('login-spinner');

        btn.disabled = true;
        spinner.classList.remove('d-none');
        errorDiv.classList.add('d-none');

        try {
            const response = await fetch('/api/auth/login/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password, remember_me: rememberMe }),
            });
            const data = await response.json();

            if (response.ok) {
                saveTokens(data.tokens.access, data.tokens.refresh, data.user);
                redirectByRole(data.user);
            } else if (response.status === 403 && data.error === 'email_not_verified') {
                window.location.href = `/verify-email/?email=${encodeURIComponent(data.email || email)}`;
            } else if (response.status === 429) {
                errorDiv.className = 'alert alert-danger';
                document.getElementById('login-error-msg').textContent = data.detail || 'Забагато спроб. Зачекайте 1 хвилину.';
                errorDiv.classList.remove('d-none');
            } else {
                errorDiv.className = 'alert alert-danger';
                const errors = data.non_field_errors || data.detail || 'Невірний email або пароль.';
                document.getElementById('login-error-msg').textContent = Array.isArray(errors) ? errors[0] : errors;
                errorDiv.classList.remove('d-none');
            }
        } catch (e) {
            errorDiv.className = 'alert alert-danger';
            document.getElementById('login-error-msg').textContent = 'Помилка з\'єднання. Спробуйте знову.';
            errorDiv.classList.remove('d-none');
        } finally {
            btn.disabled = false;
            spinner.classList.add('d-none');
        }
    };

    loginBtn?.addEventListener('click', doLogin);
    document.getElementById('login-password')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') doLogin();
    });
}

function setupTogglePassword() {
    const toggleBtn = document.getElementById('toggle-password');
    const passInput = document.getElementById('login-password');
    if (!toggleBtn || !passInput) return;
    toggleBtn.addEventListener('click', () => {
        const isPassword = passInput.type === 'password';
        passInput.type = isPassword ? 'text' : 'password';
        toggleBtn.querySelector('i').className = isPassword ? 'bi bi-eye-slash' : 'bi bi-eye';
    });
}

function redirectByRole(user = null) {
    const currentUser = user || getCurrentUser();
    if (!currentUser) { window.location.href = '/'; return; }
    switch (currentUser.role) {
        case 'doctor': window.location.href = '/doctors/cabinet/'; break;
        case 'admin': window.location.href = '/admin-panel/'; break;
        default: window.location.href = '/profile/';
    }
}
