/**
 * ============================================
 * Mediculus Hospital - Сторінка профілю
 * ============================================
 */

document.addEventListener('DOMContentLoaded', async () => {
    if (!isAuthenticated()) {
        window.location.href = '/login/';
        return;
    }

    await loadProfile();
    setupEditProfile();
    setupChangePassword();
    setupDeleteAccount();
});

async function loadProfile() {
    try {
        const response = await apiRequest('/auth/profile/');
        if (!response || !response.ok) {
            window.location.href = '/login/';
            return;
        }

        const user = await response.json();

        // Навбар інформація
        document.getElementById('profile-name').textContent = user.full_name;
        document.getElementById('profile-email').textContent = user.email;
        document.getElementById('profile-phone').textContent = user.phone || '—';

        // Роль
        const roleLabels = { patient: 'Пацієнт', doctor: 'Лікар', admin: 'Адміністратор' };
        document.getElementById('profile-role-badge').textContent = roleLabels[user.role] || user.role;

        // Заповнення даних
        document.getElementById('p-first-name').textContent = user.first_name;
        document.getElementById('p-last-name').textContent = user.last_name;
        document.getElementById('p-email').textContent = user.email;
        document.getElementById('p-phone').textContent = user.phone || '—';

        // По-батькові
        document.getElementById('p-patronymic').textContent = user.patronymic || '—';

        if (user.patient_profile) {
            document.getElementById('p-dob').textContent =
                user.patient_profile.date_of_birth
                    ? new Date(user.patient_profile.date_of_birth).toLocaleDateString('uk-UA')
                    : '—';
            document.getElementById('p-age').textContent =
                user.patient_profile.age ? `${user.patient_profile.age} р.` : '—';
            document.getElementById('p-gender').textContent =
                user.patient_profile.gender_display || '—';
        }

        // Показуємо секцію залежно від ролі
        if (user.role === 'doctor') {
            document.getElementById('patient-section')?.classList.add('d-none');
            document.getElementById('doctor-section')?.classList.remove('d-none');
            await loadDoctorPhoto();
            setupDoctorPhotoUpload();
            setupDoctorPhotoDelete();
        } else if (user.role === 'admin') {
            window.location.href = '/admin-panel/';
        }

        // Show delete section for patients
        if (user.role === 'patient') {
            const deleteSection = document.getElementById('delete-account-section');
            if (deleteSection) deleteSection.style.removeProperty('display');
        }

    } catch (e) {
        console.error('Помилка завантаження профілю:', e);
    }
}

/**
 * Завантаження фото лікаря та відображення в лівій панелі.
 */
async function loadDoctorPhoto() {
    try {
        const response = await apiRequest('/doctors/me/');
        if (!response || !response.ok) return;
        const doctor = await response.json();

        if (doctor.photo_url) {
            // Ліва панель
            const avatarPhoto = document.getElementById('profile-avatar-photo');
            const avatarIcon = document.getElementById('profile-avatar-icon');
            if (avatarPhoto) {
                avatarPhoto.src = doctor.photo_url;
                avatarPhoto.classList.remove('d-none');
            }
            if (avatarIcon) avatarIcon.classList.add('d-none');

            // Секція лікаря
            const doctorPhoto = document.getElementById('doctor-profile-photo');
            if (doctorPhoto) doctorPhoto.src = doctor.photo_url;

            // Показати кнопку видалення фото
            document.getElementById('delete-photo-btn')?.classList.remove('d-none');
        }
    } catch (e) {
        console.error('Помилка завантаження фото лікаря:', e);
    }
}

/**
 * Видалення фото лікаря.
 */
function setupDoctorPhotoDelete() {
    const confirmBtn = document.getElementById('confirm-delete-photo-btn');
    if (!confirmBtn) return;

    confirmBtn.addEventListener('click', async () => {
        const spinner = document.getElementById('delete-photo-spinner');
        confirmBtn.disabled = true;
        spinner?.classList.remove('d-none');

        try {
            const token = getAccessToken();
            const response = await fetch('/api/doctors/me/photo/', {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
            });

            if (response.ok) {
                // Закрити модалку
                bootstrap.Modal.getInstance(document.getElementById('deletePhotoModal'))?.hide();

                // Замінити на заглушку
                const profilePhoto = document.getElementById('doctor-profile-photo');
                const avatarPhoto = document.getElementById('profile-avatar-photo');
                const avatarIcon = document.getElementById('profile-avatar-icon');

                if (profilePhoto) profilePhoto.src = '/static/images/doctor-default.svg';
                if (avatarPhoto) { avatarPhoto.classList.add('d-none'); avatarPhoto.src = ''; }
                if (avatarIcon) avatarIcon.classList.remove('d-none');

                // Сховати кнопку "Видалити фото"
                document.getElementById('delete-photo-btn')?.classList.add('d-none');

                // Показати повідомлення успіху
                const successEl = document.getElementById('photo-upload-success');
                if (successEl) {
                    successEl.innerHTML = '<i class="bi bi-check-circle me-1"></i>Фото видалено.';
                    successEl.classList.remove('d-none');
                    setTimeout(() => successEl.classList.add('d-none'), 3000);
                }
            } else {
                const data = await response.json();
                const errorEl = document.getElementById('photo-upload-error');
                if (errorEl) {
                    errorEl.textContent = data.error || 'Помилка видалення фото.';
                    errorEl.classList.remove('d-none');
                }
            }
        } catch (e) {
            const errorEl = document.getElementById('photo-upload-error');
            if (errorEl) { errorEl.textContent = 'Помилка з\'єднання.'; errorEl.classList.remove('d-none'); }
        } finally {
            confirmBtn.disabled = false;
            spinner?.classList.add('d-none');
        }
    });
}

/**
 * Завантаження нового фото лікаря.
 */
function setupDoctorPhotoUpload() {
    const photoInput = document.getElementById('doctor-photo-upload');
    if (!photoInput) return;

    photoInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const successEl = document.getElementById('photo-upload-success');
        const errorEl = document.getElementById('photo-upload-error');
        successEl?.classList.add('d-none');
        errorEl?.classList.add('d-none');

        if (file.size > 5 * 1024 * 1024) {
            if (errorEl) {
                errorEl.textContent = 'Розмір файлу не може перевищувати 5 МБ.';
                errorEl.classList.remove('d-none');
            }
            return;
        }

        const formData = new FormData();
        formData.append('photo', file);

        try {
            const token = getAccessToken();
            const response = await fetch('/api/doctors/me/photo/', {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData,
            });

            if (response.ok) {
                const data = await response.json();
                if (data.photo_url) {
                    // Оновлюємо обидва місця
                    document.getElementById('doctor-profile-photo').src = data.photo_url;

                    const avatarPhoto = document.getElementById('profile-avatar-photo');
                    const avatarIcon = document.getElementById('profile-avatar-icon');
                    if (avatarPhoto) {
                        avatarPhoto.src = data.photo_url;
                        avatarPhoto.classList.remove('d-none');
                    }
                    if (avatarIcon) avatarIcon.classList.add('d-none');

                    // Показати кнопку видалення фото
                    document.getElementById('delete-photo-btn')?.classList.remove('d-none');
                }
                successEl?.classList.remove('d-none');
            } else {
                const data = await response.json();
                if (errorEl) {
                    errorEl.textContent = Object.values(data).flat().join(' ') || 'Помилка завантаження.';
                    errorEl.classList.remove('d-none');
                }
            }
        } catch (e) {
            if (errorEl) {
                errorEl.textContent = 'Помилка з\'єднання.';
                errorEl.classList.remove('d-none');
            }
        }
    });
}

/**
 * Налаштування редагування профілю (телефон).
 */
function setupEditProfile() {
    const editBtn = document.getElementById('edit-profile-btn');
    const cancelBtn = document.getElementById('cancel-edit-btn');
    const saveBtn = document.getElementById('save-profile-btn');

    // Зберігаємо оригінальне значення телефону при відкритті форми
    let originalPhone = '';

    editBtn?.addEventListener('click', () => {
        const currentPhone = document.getElementById('p-phone')?.textContent;
        const phoneValue = currentPhone === '—' ? '' : currentPhone;
        originalPhone = phoneValue;
        document.getElementById('edit-phone').value = phoneValue;

        document.getElementById('profile-view-mode').classList.add('d-none');
        document.getElementById('profile-edit-mode').classList.remove('d-none');

        document.getElementById('edit-success').classList.add('d-none');
        document.getElementById('edit-error').classList.add('d-none');
    });

    cancelBtn?.addEventListener('click', () => {
        document.getElementById('profile-view-mode').classList.remove('d-none');
        document.getElementById('profile-edit-mode').classList.add('d-none');
    });

    saveBtn?.addEventListener('click', async () => {
        const phone = document.getElementById('edit-phone').value.trim();
        const spinner = document.getElementById('save-spinner');
        const successEl = document.getElementById('edit-success');
        const errorEl = document.getElementById('edit-error');

        successEl.classList.add('d-none');
        errorEl.classList.add('d-none');

        // Якщо значення не змінилось — просто закриваємо форму
        if (phone === originalPhone) {
            document.getElementById('profile-view-mode').classList.remove('d-none');
            document.getElementById('profile-edit-mode').classList.add('d-none');
            return;
        }

        saveBtn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            const response = await apiRequest('/auth/profile/', {
                method: 'PATCH',
                body: JSON.stringify({ phone }),
            });

            const data = await response.json();

            if (response.ok) {
                originalPhone = data.phone || '';
                document.getElementById('p-phone').textContent = data.phone || '—';
                document.getElementById('profile-phone').textContent = data.phone || '—';
                successEl.classList.remove('d-none');

                setTimeout(() => {
                    document.getElementById('profile-view-mode').classList.remove('d-none');
                    document.getElementById('profile-edit-mode').classList.add('d-none');
                }, 1500);
            } else {
                const errors = Object.values(data).flat().join(' ');
                errorEl.textContent = errors || 'Помилка збереження.';
                errorEl.classList.remove('d-none');
            }
        } catch (e) {
            errorEl.textContent = 'Помилка з\'єднання.';
            errorEl.classList.remove('d-none');
        } finally {
            saveBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    });
}

/**
 * Видалення акаунту пацієнта.
 */
function setupDeleteAccount() {
    const deleteBtn = document.getElementById('delete-account-btn');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    if (!deleteBtn) return;

    confirmDeleteBtn?.addEventListener('click', async () => {
        const password = document.getElementById('delete-password')?.value || '';
        const errorEl = document.getElementById('delete-error');
        const spinner = document.getElementById('delete-spinner');

        if (!password) {
            if (errorEl) { errorEl.textContent = 'Введіть пароль.'; errorEl.classList.remove('d-none'); }
            return;
        }

        confirmDeleteBtn.disabled = true;
        spinner?.classList.remove('d-none');
        errorEl?.classList.add('d-none');

        try {
            const response = await apiRequest('/auth/delete-account/', {
                method: 'POST',
                body: JSON.stringify({ password }),
            });
            const data = await response.json();

            if (response.ok) {
                clearAuth();
                window.location.href = '/?account_deleted=1';
            } else {
                if (errorEl) { errorEl.textContent = data.error || 'Помилка.'; errorEl.classList.remove('d-none'); }
                confirmDeleteBtn.disabled = false;
            }
        } catch (e) {
            if (errorEl) { errorEl.textContent = 'Помилка з\'єднання.'; errorEl.classList.remove('d-none'); }
            confirmDeleteBtn.disabled = false;
        } finally {
            spinner?.classList.add('d-none');
        }
    });
}

/**
 * Налаштування зміни пароля (згорнута форма).
 */
function setupChangePassword() {
    const toggleBtn = document.getElementById('toggle-password-form-btn');
    const cancelBtn = document.getElementById('cancel-password-btn');
    const formBody = document.getElementById('password-form-body');
    const changeBtn = document.getElementById('change-password-btn');
    if (!changeBtn) return;

    // Розгорнути/згорнути форму
    toggleBtn?.addEventListener('click', () => {
        formBody?.classList.remove('d-none');
        toggleBtn.classList.add('d-none');
    });

    cancelBtn?.addEventListener('click', () => {
        formBody?.classList.add('d-none');
        toggleBtn?.classList.remove('d-none');
        document.getElementById('pw-old').value = '';
        document.getElementById('pw-new').value = '';
        document.getElementById('pw-confirm').value = '';
        document.getElementById('pw-success')?.classList.add('d-none');
        document.getElementById('pw-error')?.classList.add('d-none');
    });

    changeBtn.addEventListener('click', async () => {
        const oldPassword = document.getElementById('pw-old').value;
        const newPassword = document.getElementById('pw-new').value;
        const confirmPassword = document.getElementById('pw-confirm').value;
        const spinner = document.getElementById('pw-spinner');
        const successEl = document.getElementById('pw-success');
        const errorEl = document.getElementById('pw-error');

        successEl.classList.add('d-none');
        errorEl.classList.add('d-none');

        if (!oldPassword || !newPassword || !confirmPassword) {
            errorEl.textContent = 'Заповніть всі поля.';
            errorEl.classList.remove('d-none');
            return;
        }

        // Клієнтська валідація пароля
        if (newPassword.length < 8) {
            errorEl.textContent = 'Пароль має містити мінімум 8 символів.';
            errorEl.classList.remove('d-none');
            return;
        }
        if (!/[a-zA-Zа-яА-ЯіІїЇєЄґҐ]/.test(newPassword)) {
            errorEl.textContent = 'Пароль має містити хоча б одну літеру.';
            errorEl.classList.remove('d-none');
            return;
        }
        if (!/\d/.test(newPassword)) {
            errorEl.textContent = 'Пароль має містити хоча б одну цифру.';
            errorEl.classList.remove('d-none');
            return;
        }

        changeBtn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            const response = await apiRequest('/auth/change-password/', {
                method: 'POST',
                body: JSON.stringify({
                    old_password: oldPassword,
                    new_password: newPassword,
                    new_password_confirm: confirmPassword,
                }),
            });

            const data = await response.json();

            if (response.ok) {
                successEl.classList.remove('d-none');
                document.getElementById('pw-old').value = '';
                document.getElementById('pw-new').value = '';
                document.getElementById('pw-confirm').value = '';
                // Згорнути форму через 2 секунди
                setTimeout(() => {
                    formBody?.classList.add('d-none');
                    toggleBtn?.classList.remove('d-none');
                    successEl.classList.add('d-none');
                }, 2000);
            } else {
                errorEl.textContent = data.error || 'Помилка зміни пароля.';
                errorEl.classList.remove('d-none');
            }
        } catch (e) {
            errorEl.textContent = 'Помилка з\'єднання.';
            errorEl.classList.remove('d-none');
        } finally {
            changeBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    });
}
