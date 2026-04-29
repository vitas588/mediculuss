/**
 * Mediculus — Відновлення пароля
 */
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('fp-btn')?.addEventListener('click', sendReset);
    document.getElementById('fp-email')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendReset();
    });
});

async function sendReset() {
    const email = document.getElementById('fp-email')?.value.trim() || '';
    const btn = document.getElementById('fp-btn');
    const spinner = document.getElementById('fp-spinner');

    document.getElementById('fp-error').classList.add('d-none');
    document.getElementById('fp-success').classList.add('d-none');

    if (!email) {
        document.getElementById('fp-error-msg').textContent = 'Введіть email.';
        document.getElementById('fp-error').classList.remove('d-none');
        return;
    }

    btn.disabled = true;
    spinner.classList.remove('d-none');

    try {
        const response = await fetch('/api/auth/forgot-password/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email }),
        });
        const data = await response.json();

        document.getElementById('fp-success-msg').textContent = data.message || 'Лист надіслано.';
        document.getElementById('fp-success').classList.remove('d-none');
        btn.disabled = true; // Prevent spam
    } catch (e) {
        document.getElementById('fp-error-msg').textContent = 'Помилка з\'єднання.';
        document.getElementById('fp-error').classList.remove('d-none');
        btn.disabled = false;
    } finally {
        spinner.classList.add('d-none');
    }
}
