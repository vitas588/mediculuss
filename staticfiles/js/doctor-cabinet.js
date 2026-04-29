/**
 * ============================================
 * Mediculus Hospital - Кабінет лікаря
 * ============================================
 */

document.addEventListener('DOMContentLoaded', async () => {
    const user = getCurrentUser();

    if (!isAuthenticated() || !user || user.role !== 'doctor') {
        window.location.href = '/login/';
        return;
    }

    // Дата сьогодні
    const todayEl = document.getElementById('today-date');
    if (todayEl) {
        todayEl.textContent = new Date().toLocaleDateString('uk-UA', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        });
    }

    document.getElementById('cabinet-subtitle').textContent =
        `Ласкаво просимо, ${user.full_name}!`;

    await Promise.all([
        loadDoctorProfile(),
        loadTodayAppointments(),
        loadSchedule(),
    ]);

    setupPhotoUpload();
    setupCompleteModal();
});

/**
 * Завантаження профілю лікаря.
 */
async function loadDoctorProfile() {
    try {
        const response = await apiRequest('/auth/profile/');
        if (!response || !response.ok) return;
        const user = await response.json();

        // Знайдемо профіль лікаря через публічний API
        const allResponse = await fetch(`/api/doctors/?search=${encodeURIComponent(user.first_name)}`);
        const allData = await allResponse.json();
        const doctors = allData.results || allData;

        // Знаходимо поточного лікаря за email
        // (Публічний API не повертає email — шукаємо за ім'ям)
        // У реальному проєкті додали б /api/doctors/me/ endpoint
        if (doctors.length > 0) {
            const doctor = doctors[0]; // Спрощення для демо
            document.getElementById('cabinet-name').textContent = doctor.full_name;
            document.getElementById('cabinet-specialty').textContent = doctor.specialty_name;
            document.getElementById('cabinet-experience').textContent = `${doctor.experience_years} років`;
            document.getElementById('cabinet-slot-duration').textContent = `${doctor.slot_duration} хв`;

            if (doctor.photo_url) {
                document.getElementById('cabinet-photo').src = doctor.photo_url;
            }
        }
    } catch (e) {
        console.error('Помилка завантаження профілю:', e);
    }
}

/**
 * Завантаження записів на сьогодні та підрахунок статистики.
 */
async function loadTodayAppointments() {
    const container = document.getElementById('today-appointments');
    if (!container) return;

    try {
        const today = new Date().toISOString().split('T')[0];

        // Встановлюємо href для картки "Сьогодні" з датою
        const todayCard = document.getElementById('stat-card-today');
        if (todayCard) todayCard.href = `/appointments/doctor/?date=${today}&status=planned`;

        // Паралельно завантажуємо: заплановані, завершені, всі записи
        const [plannedResp, completedResp, allResp] = await Promise.all([
            apiRequest('/appointments/?status=planned'),
            apiRequest('/appointments/?status=completed'),
            apiRequest('/appointments/'),
        ]);

        // Заплановані — використовуємо count (загальна кількість, не тільки перша сторінка)
        if (plannedResp && plannedResp.ok) {
            const plannedData = await plannedResp.json();
            const plannedResults = plannedData.results || (Array.isArray(plannedData) ? plannedData : []);
            const todayApts = plannedResults.filter(apt => apt.date_time.startsWith(today));

            document.getElementById('stat-today').textContent = todayApts.length;
            document.getElementById('stat-upcoming').textContent =
                plannedData.count ?? plannedResults.length;

            // Рендеримо список сьогоднішніх записів
            renderTodayList(container, todayApts);
        }

        // Завершені — використовуємо count
        if (completedResp && completedResp.ok) {
            const completedData = await completedResp.json();
            document.getElementById('stat-completed').textContent =
                completedData.count ?? (completedData.results || completedData).length;
        }

        // Всього пацієнтів — унікальні серед ВСІХ записів (будь-який статус)
        if (allResp && allResp.ok) {
            const allData = await allResp.json();
            const allResults = allData.results || (Array.isArray(allData) ? allData : []);
            const uniquePatients = new Set(allResults.map(a => a.patient_name)).size;
            document.getElementById('stat-total').textContent = uniquePatients;
        }

    } catch (e) {
        console.error('Помилка:', e);
        container.innerHTML = '<div class="text-center text-muted py-3">Помилка завантаження</div>';
    }
}

/**
 * Рендер списку записів на сьогодні.
 */
function renderTodayList(container, todayApts) {
    if (todayApts.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="bi bi-calendar-check fs-1 d-block mb-2"></i>
                На сьогодні немає записів
            </div>`;
        return;
    }

    const now = new Date();

    container.innerHTML = todayApts.map(apt => {
        const dt = new Date(apt.date_time);
        const time = dt.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });

        // Кнопка "Завершити" — disabled з tooltip якщо час ще не настав
        let completeBtnHtml;
        if (dt <= now) {
            completeBtnHtml = `
                <button class="btn btn-sm btn-success complete-btn"
                        data-id="${apt.id}"
                        data-patient="${escapeHtml(apt.patient_name)}">
                    <i class="bi bi-check-circle me-1"></i>Завершити
                </button>`;
        } else {
            completeBtnHtml = `
                <span data-bs-toggle="tooltip" title="Прийом ще не розпочався" tabindex="0">
                    <button class="btn btn-sm btn-success" disabled style="pointer-events:none;">
                        <i class="bi bi-check-circle me-1"></i>Завершити
                    </button>
                </span>`;
        }

        return `
            <div class="d-flex align-items-center justify-content-between border-bottom px-4 py-3">
                <div class="d-flex align-items-center gap-3">
                    <div class="fw-bold text-primary" style="min-width:50px">${time}</div>
                    <div>
                        <p class="fw-semibold mb-0">${escapeHtml(apt.patient_name)}</p>
                        <small class="text-muted">${apt.reason ? escapeHtml(apt.reason.slice(0,40)) : 'Без нотаток'}</small>
                    </div>
                </div>
                <div class="d-flex gap-2">
                    <a href="/appointments/${apt.id}/" class="btn btn-sm btn-outline-primary">
                        <i class="bi bi-eye"></i>
                    </a>
                    ${completeBtnHtml}
                </div>
            </div>`;
    }).join('');

    // Ініціалізуємо Bootstrap tooltips на disabled кнопках
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });

    setupCompleteButtons();
}

/**
 * Завантаження розкладу лікаря.
 */
async function loadSchedule() {
    const container = document.getElementById('cabinet-schedule');
    if (!container) return;

    try {
        const response = await apiRequest('/doctors/me/schedule/');
        if (!response || !response.ok) return;

        const schedules = await response.json();
        const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд'];

        container.innerHTML = dayNames.map((day, i) => {
            const s = schedules.find ? schedules.find(sch => sch.day_of_week === i) : null;
            const results = Array.isArray(schedules) ? schedules : (schedules.results || []);
            const schedule = results.find(sch => sch.day_of_week === i);

            if (!schedule || !schedule.is_working) {
                return `<div class="schedule-row">
                    <span class="schedule-day">${day}</span>
                    <span class="schedule-closed">Вихідний</span>
                </div>`;
            }
            return `<div class="schedule-row">
                <span class="schedule-day">${day}</span>
                <span class="schedule-time">${schedule.work_start.slice(0,5)}–${schedule.work_end.slice(0,5)}</span>
            </div>`;
        }).join('');
    } catch (e) {
        container.innerHTML = '<small class="text-muted">Розклад недоступний</small>';
    }
}

/**
 * Налаштування кнопок "Завершити прийом".
 */
function setupCompleteButtons() {
    document.querySelectorAll('.complete-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const modal = new bootstrap.Modal(document.getElementById('completeModal'));
            document.getElementById('complete-appointment-id').value = btn.dataset.id;
            document.getElementById('complete-patient-name').textContent = btn.dataset.patient;
            document.getElementById('complete-diagnosis').value = '';
            document.getElementById('complete-treatment').value = '';
            document.getElementById('complete-notes').value = '';
            document.getElementById('complete-error').classList.add('d-none');
            modal.show();
        });
    });
}

/**
 * Налаштування модального вікна завершення прийому.
 */
function setupCompleteModal() {
    const confirmBtn = document.getElementById('complete-confirm-btn');
    if (!confirmBtn) return;

    confirmBtn.addEventListener('click', async () => {
        const appointmentId = document.getElementById('complete-appointment-id').value;
        const diagnosis = document.getElementById('complete-diagnosis').value.trim();
        const treatment = document.getElementById('complete-treatment').value.trim();
        const notes = document.getElementById('complete-notes').value.trim();
        const errorDiv = document.getElementById('complete-error');

        if (!diagnosis || !treatment) {
            errorDiv.textContent = 'Діагноз та призначення обов\'язкові.';
            errorDiv.classList.remove('d-none');
            return;
        }

        confirmBtn.disabled = true;
        errorDiv.classList.add('d-none');

        try {
            const response = await apiRequest(`/appointments/${appointmentId}/complete/`, {
                method: 'PATCH',
                body: JSON.stringify({ diagnosis, treatment, doctor_notes: notes }),
            });

            if (response && response.ok) {
                bootstrap.Modal.getInstance(document.getElementById('completeModal')).hide();
                await loadTodayAppointments();
            } else {
                const data = await response?.json();
                errorDiv.textContent = data?.error || 'Помилка завершення прийому.';
                errorDiv.classList.remove('d-none');
            }
        } catch (e) {
            errorDiv.textContent = 'Помилка з\'єднання.';
            errorDiv.classList.remove('d-none');
        } finally {
            confirmBtn.disabled = false;
        }
    });
}

/**
 * Завантаження фото лікаря.
 */
function setupPhotoUpload() {
    const photoInput = document.getElementById('photo-upload');
    if (!photoInput) return;

    photoInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Перевірка розміру (5 МБ)
        if (file.size > 5 * 1024 * 1024) {
            alert('Розмір файлу не може перевищувати 5 МБ.');
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
                    document.getElementById('cabinet-photo').src = data.photo_url;
                }
                alert('Фото успішно оновлено!');
            } else {
                const data = await response.json();
                alert(Object.values(data).flat().join(' ') || 'Помилка завантаження фото.');
            }
        } catch (e) {
            alert('Помилка з\'єднання.');
        }
    });
}
