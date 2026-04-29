/**
 * Mediculus — Скидання пароля
 */
document.addEventListener('DOMContentLoaded', async () => {
    // Перевірка наявності токена
    if (typeof RESET_TOKEN === 'undefined' || !RESET_TOKEN) {
        showInvalid('Недійсне посилання. Запросіть нове посилання для відновлення паролю.');
        return;
    }

    // Перевірка валідності токена через API
    try {
        const response = await fetch(
            `/api/auth/reset-password/?token=${encodeURIComponent(RESET_TOKEN)}`
        );
        const data = await response.json();
        if (!data.valid) {
            showInvalid(
                data.error ||
                'Посилання недійсне або вже використане. Запросіть нове посилання для відновлення паролю.'
            );
            return;
        }
    } catch (e) {
        // При помилці мережі — дозволяємо показати форму, помилка буде при сабміті
    }

    // Токен валідний — показуємо форму
    document.getElementById('rp-btn')?.addEventListener('click', resetPassword);
    document.getElementById('rp-toggle')?.addEventListener('click', () => {
        const input = document.getElementById('rp-password');
        const icon = document.getElementById('rp-toggle').querySelector('i');
        input.type = input.type === 'password' ? 'text' : 'password';
        icon.className = input.type === 'password' ? 'bi bi-eye' : 'bi bi-eye-slash';
    });
});

function showInvalid(msg) {
    document.getElementById('rp-invalid-msg').textContent = msg;
    document.getElementById('rp-invalid')?.classList.remove('d-none');
    document.getElementById('rp-form-card')?.classList.add('d-none');
}

function showError(msg) {
    document.getElementById('rp-error-msg').textContent = msg;
    document.getElementById('rp-error').classList.remove('d-none');
    document.getElementById('rp-success').classList.add('d-none');
}

function showSuccess(msg) {
    document.getElementById('rp-success-msg').textContent = msg;
    document.getElementById('rp-success').classList.remove('d-none');
    document.getElementById('rp-error').classList.add('d-none');
}

async function resetPassword() {
    const newPassword = document.getElementById('rp-password')?.value || '';
    const confirm = document.getElementById('rp-password-confirm')?.value || '';
    const btn = document.getElementById('rp-btn');
    const spinner = document.getElementById('rp-spinner');

    document.getElementById('rp-error').classList.add('d-none');

    if (newPassword.length < 8) { showError('Пароль має містити мінімум 8 символів.'); return; }
    if (!/[a-zA-Zа-яА-ЯіІїЇєЄґҐ]/.test(newPassword)) { showError('Пароль має містити хоча б одну літеру.'); return; }
    if (!/\d/.test(newPassword)) { showError('Пароль має містити хоча б одну цифру.'); return; }
    if (newPassword !== confirm) { showError('Паролі не співпадають.'); return; }

    btn.disabled = true;
    spinner.classList.remove('d-none');

    try {
        const response = await fetch('/api/auth/reset-password/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: RESET_TOKEN, new_password: newPassword, new_password_confirm: confirm }),
        });
        const data = await response.json();

        if (response.ok) {
            showSuccess(data.message || 'Пароль успішно змінено. Тепер ви можете увійти.');
            document.getElementById('rp-form-card')?.classList.add('d-none');
            document.getElementById('rp-login-link')?.classList.remove('d-none');
        } else {
            showError(data.error || 'Помилка зміни пароля.');
            btn.disabled = false;
        }
    } catch (e) {
        showError('Помилка з\'єднання.');
        btn.disabled = false;
    } finally {
        spinner.classList.add('d-none');
    }
}
