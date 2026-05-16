/**
 * ============================================
 * Mediculus Hospital - Сторінка реєстрації
 * ============================================
 */

document.addEventListener('DOMContentLoaded', () => {
    if (isAuthenticated()) {
        window.location.href = '/profile/';
        return;
    }

    // Встановлюємо максимальну дату народження (сьогодні)
    const dobInput = document.getElementById('reg-dob');
    if (dobInput) {
        dobInput.max = new Date().toISOString().split('T')[0];
    }

    setupRegisterForm();
    setupTogglePassword();

    // Disable submit until privacy is checked
    const privacyCheck = document.getElementById('reg-privacy');
    const submitBtn = document.getElementById('register-btn');
    if (privacyCheck && submitBtn) {
        submitBtn.disabled = true;
        privacyCheck.addEventListener('change', () => {
            submitBtn.disabled = !privacyCheck.checked;
        });
    }
});

function setupRegisterForm() {
    const form = document.getElementById('register-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const errorDiv = document.getElementById('register-error');
        const errorMsg = document.getElementById('register-error-msg');
        const btn = document.getElementById('register-btn');
        const spinner = document.getElementById('register-spinner');

        errorDiv.classList.add('d-none');

        // Валідація погодження з політикою
        const privacyCheck = document.getElementById('reg-privacy');
        if (!privacyCheck?.checked) {
            errorMsg.textContent = 'Ви маєте погодитись з Політикою конфіденційності.';
            errorDiv.classList.remove('d-none');
            return;
        }

        // Валідація дати народження
        const dobValue = document.getElementById('reg-dob').value;
        if (dobValue) {
            const dob = new Date(dobValue);
            const today = new Date();
            today.setHours(0, 0, 0, 0);

            if (dob > today) {
                errorMsg.textContent = 'Дата народження не може бути в майбутньому.';
                errorDiv.classList.remove('d-none');
                return;
            }
            if (dob.getFullYear() < 1900) {
                errorMsg.textContent = 'Рік народження не може бути раніше 1900.';
                errorDiv.classList.remove('d-none');
                return;
            }
            const ageMs = today - dob;
            const ageYears = ageMs / (1000 * 60 * 60 * 24 * 365.25);
            if (ageYears < 1) {
                errorMsg.textContent = 'Вік пацієнта має бути не менше 1 року.';
                errorDiv.classList.remove('d-none');
                return;
            }
        }

        // Валідація паролів
        const password = document.getElementById('reg-password').value;
        const passwordConfirm = document.getElementById('reg-password-confirm').value;
        if (password !== passwordConfirm) {
            errorMsg.textContent = 'Паролі не співпадають.';
            errorDiv.classList.remove('d-none');
            return;
        }
        if (password.length < 8) {
            errorMsg.textContent = 'Пароль має містити мінімум 8 символів.';
            errorDiv.classList.remove('d-none');
            return;
        }
        if (!/[a-zA-Zа-яА-ЯіІїЇєЄґҐ]/.test(password)) {
            errorMsg.textContent = 'Пароль має містити хоча б одну літеру.';
            errorDiv.classList.remove('d-none');
            return;
        }
        if (!/\d/.test(password)) {
            errorMsg.textContent = 'Пароль має містити хоча б одну цифру.';
            errorDiv.classList.remove('d-none');
            return;
        }

        const formData = {
            first_name: document.getElementById('reg-first-name').value.trim(),
            last_name: document.getElementById('reg-last-name').value.trim(),
            patronymic: document.getElementById('reg-patronymic').value.trim(),
            email: document.getElementById('reg-email').value.trim(),
            phone: document.getElementById('reg-phone').value.trim(),
            date_of_birth: document.getElementById('reg-dob').value || null,
            gender: document.getElementById('reg-gender').value,
            password,
            password_confirm: passwordConfirm,
        };

        btn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            const response = await fetch('/api/auth/register/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            });

            const data = await response.json();

            if (response.ok) {
                const userEmail = encodeURIComponent(formData.email);
                window.location.href = `/verify-email/?email=${userEmail}`;
            } else {
                // Збираємо всі помилки в один рядок
                const errors = Object.values(data).flat().join(' ');
                errorMsg.textContent = errors || 'Помилка реєстрації. Перевірте дані.';
                errorDiv.classList.remove('d-none');
            }
        } catch (e) {
            errorMsg.textContent = 'Помилка з\'єднання.';
            errorDiv.classList.remove('d-none');
        } finally {
            btn.disabled = false;
            spinner.classList.add('d-none');
        }
    });
}

function setupTogglePassword() {
    const btn = document.getElementById('toggle-pass');
    const input = document.getElementById('reg-password');
    if (!btn || !input) return;

    btn.addEventListener('click', () => {
        const isPass = input.type === 'password';
        input.type = isPass ? 'text' : 'password';
        btn.querySelector('i').className = isPass ? 'bi bi-eye-slash' : 'bi bi-eye';
    });
}
