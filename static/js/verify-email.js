/**
 * Mediculus — Підтвердження email
 */
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const email = params.get('email') || '';

    const emailDisplay = document.getElementById('verify-email-display');
    if (emailDisplay) emailDisplay.textContent = email || 'невідомо';

    const codeInput = document.getElementById('verify-code');
    if (codeInput) {
        // Only digits
        codeInput.addEventListener('input', () => {
            codeInput.value = codeInput.value.replace(/\D/g, '').slice(0, 6);
        });
        codeInput.focus();
    }

    document.getElementById('verify-btn')?.addEventListener('click', verify);
    document.getElementById('resend-btn')?.addEventListener('click', resend);
});

function showError(msg) {
    const el = document.getElementById('verify-error');
    document.getElementById('verify-error-msg').textContent = msg;
    el.classList.remove('d-none');
    document.getElementById('verify-success').classList.add('d-none');
}

function showSuccess(msg) {
    const el = document.getElementById('verify-success');
    document.getElementById('verify-success-msg').textContent = msg;
    el.classList.remove('d-none');
    document.getElementById('verify-error').classList.add('d-none');
}

async function verify() {
    const params = new URLSearchParams(window.location.search);
    const email = params.get('email') || '';
    const code = document.getElementById('verify-code')?.value.trim() || '';

    if (!email) { showError('Email не вказано. Поверніться на сторінку реєстрації.'); return; }
    if (code.length !== 6) { showError('Введіть 6-значний код.'); return; }

    const btn = document.getElementById('verify-btn');
    const spinner = document.getElementById('verify-spinner');
    btn.disabled = true;
    spinner.classList.remove('d-none');

    try {
        const response = await fetch('/api/auth/verify-email/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, code }),
        });
        const data = await response.json();

        if (response.ok) {
            showSuccess(data.message || 'Email підтверджено!');
            if (data.tokens) {
                saveTokens(data.tokens.access, data.tokens.refresh, data.user);
            }
            document.getElementById('verify-profile-link')?.classList.remove('d-none');
            // Сховати форму введення коду після успіху
            document.getElementById('verify-code')?.closest('.mb-3')?.classList.add('d-none');
            document.getElementById('verify-btn')?.classList.add('d-none');
        } else {
            showError(data.error || 'Помилка підтвердження.');
        }
    } catch (e) {
        showError('Помилка з\'єднання.');
    } finally {
        btn.disabled = false;
        spinner.classList.add('d-none');
    }
}

async function resend() {
    const params = new URLSearchParams(window.location.search);
    const email = params.get('email') || '';
    if (!email) { showError('Email не вказано.'); return; }

    const btn = document.getElementById('resend-btn');
    const spinner = document.getElementById('resend-spinner');
    btn.disabled = true;
    spinner.classList.remove('d-none');

    try {
        const response = await fetch('/api/auth/resend-verification/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email }),
        });
        const data = await response.json();
        showSuccess(data.message || 'Код надіслано повторно.');
    } catch (e) {
        showError('Помилка надсилання.');
    } finally {
        setTimeout(() => { btn.disabled = false; }, 30000); // 30s cooldown
        spinner.classList.add('d-none');
    }
}
