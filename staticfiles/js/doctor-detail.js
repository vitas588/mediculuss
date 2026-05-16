/**
 * ============================================
 * Mediculus Hospital - Профіль лікаря
 * ============================================
 * DOCTOR_ID передається з Django template.
 */

function getYearsWord(years) {
    const lastTwo = years % 100;
    const lastOne = years % 10;
    if (lastTwo >= 11 && lastTwo <= 19) return 'років';
    if (lastOne === 1) return 'рік';
    if (lastOne >= 2 && lastOne <= 4) return 'роки';
    return 'років';
}

let selectedDateTime = null;
const DAY_NAMES = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд'];
const DAY_NAMES_FULL = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'П\'ятниця', 'Субота', 'Неділя'];

document.addEventListener('DOMContentLoaded', async () => {
    await loadDoctorProfile();
    setupBookingForm();
    autoSelectToday();
});

/**
 * Завантаження профілю лікаря.
 */
async function loadDoctorProfile() {
    const loader = document.getElementById('doctor-loader');
    const content = document.getElementById('doctor-content');

    try {
        const response = await fetch(`/api/doctors/${DOCTOR_ID}/`);
        if (!response.ok) {
            showError('Лікаря не знайдено.');
            return;
        }
        const doctor = await response.json();

        // Заповнюємо інформацію
        document.title = `${doctor.full_name} — Mediculus`;
        document.getElementById('breadcrumb-name').textContent = doctor.full_name;
        document.getElementById('doctor-name').textContent = doctor.full_name;
        document.getElementById('doctor-specialty').textContent = doctor.specialty?.name || '—';
        document.getElementById('doctor-experience').textContent = doctor.experience_years;
        document.getElementById('doctor-experience-label').textContent = `${getYearsWord(doctor.experience_years)} досвіду`;
        document.getElementById('doctor-slot').textContent = doctor.slot_duration;
        document.getElementById('doctor-description').textContent = doctor.description || 'Опис відсутній.';
        document.getElementById('doctor-email').textContent = doctor.email || '—';
        document.getElementById('doctor-phone').textContent = doctor.phone || '—';

        // Фото
        if (doctor.photo_url) {
            document.getElementById('doctor-photo').src = doctor.photo_url;
        }

        // Розклад
        renderSchedule(doctor.schedules);

        // Форма запису
        setupBookingVisibility();

        // Показуємо контент
        if (loader) loader.classList.add('d-none');
        if (content) content.classList.remove('d-none');

    } catch (e) {
        console.error(e);
        showError('Помилка завантаження профілю лікаря.');
    }
}

/**
 * Відображення розкладу лікаря.
 */
function renderSchedule(schedules) {
    const container = document.getElementById('doctor-schedule');
    if (!container || !schedules) return;

    const rows = DAY_NAMES_FULL.map((dayName, i) => {
        const schedule = schedules.find(s => s.day_of_week === i);
        if (!schedule || !schedule.is_working) {
            return `<div class="schedule-row">
                <span class="schedule-day">${dayName}</span>
                <span class="schedule-closed">Вихідний</span>
            </div>`;
        }
        return `<div class="schedule-row">
            <span class="schedule-day">${dayName}</span>
            <span class="schedule-time">${schedule.work_start.slice(0,5)} – ${schedule.work_end.slice(0,5)}</span>
        </div>`;
    });

    container.innerHTML = rows.join('');
}

/**
 * Показати форму запису залежно від стану авторизації.
 */
function setupBookingVisibility() {
    const authRequired = document.getElementById('booking-auth-required');
    const formSection = document.getElementById('booking-form-section');
    const user = getCurrentUser();

    if (!isAuthenticated()) {
        if (authRequired) authRequired.classList.remove('d-none');
        if (formSection) formSection.classList.add('d-none');
    } else if (user && user.role !== 'patient') {
        // Лікарі та адміни не можуть записуватись
        if (formSection) {
            formSection.innerHTML = '<div class="alert alert-info">Запис доступний тільки для пацієнтів.</div>';
        }
    }
}

/**
 * Налаштування форми запису.
 */
function setupBookingForm() {
    const dateInput = document.getElementById('booking-date');
    if (!dateInput) return;

    // Мінімальна дата — сьогодні
    const today = new Date();
    dateInput.min = today.toISOString().split('T')[0];

    // Максимальна дата — +14 днів
    const maxDate = new Date();
    maxDate.setDate(maxDate.getDate() + 14);
    dateInput.max = maxDate.toISOString().split('T')[0];

    dateInput.addEventListener('change', async () => {
        if (dateInput.value) {
            await loadAvailableSlots(dateInput.value);
        }
    });

    // Кнопка підтвердження запису
    const bookBtn = document.getElementById('book-btn');
    if (bookBtn) {
        bookBtn.addEventListener('click', createAppointment);
    }
}

/**
 * Автоматичний вибір сьогоднішньої дати і завантаження слотів.
 * Викликається після setupBookingForm і setupBookingVisibility.
 */
async function autoSelectToday() {
    const dateInput = document.getElementById('booking-date');
    // Форма запису може бути прихована (не авторизований або не пацієнт)
    if (!dateInput) return;

    const user = getCurrentUser();
    if (!isAuthenticated() || (user && user.role !== 'patient')) return;

    const todayStr = new Date().toISOString().split('T')[0];
    dateInput.value = todayStr;
    await loadAvailableSlots(todayStr);
}

/**
 * Завантаження вільних слотів.
 */
async function loadAvailableSlots(dateStr) {
    const slotsSection = document.getElementById('slots-section');
    const slotsGrid = document.getElementById('slots-grid');
    const slotsLoading = document.getElementById('slots-loading');
    const slotsEmpty = document.getElementById('slots-empty');
    const bookBtn = document.getElementById('book-btn');

    // Скидаємо вибраний слот
    selectedDateTime = null;
    if (bookBtn) bookBtn.disabled = true;
    document.getElementById('booking-summary')?.classList.add('d-none');

    if (slotsSection) slotsSection.style.display = 'none';
    if (slotsEmpty) slotsEmpty.classList.add('d-none');
    if (slotsLoading) slotsLoading.classList.remove('d-none');

    try {
        const response = await fetch(`/api/doctors/${DOCTOR_ID}/available-slots/?date=${dateStr}`);
        const data = await response.json();

        if (slotsLoading) slotsLoading.classList.add('d-none');

        if (!response.ok || !data.slots || data.slots.length === 0) {
            if (slotsEmpty) {
                slotsEmpty.textContent = data.message || 'На цю дату немає вільних слотів.';
                slotsEmpty.classList.remove('d-none');
            }
            // Ховаємо нотатки та summary — слот не вибрано
            const notesSection = document.getElementById('booking-reason-section');
            if (notesSection) notesSection.style.display = 'none';
            document.getElementById('booking-summary')?.classList.add('d-none');
            return;
        }

        // Рендеримо слоти
        if (slotsGrid) {
            slotsGrid.innerHTML = data.slots.map(slot => `
                <button class="btn btn-outline-primary slot-btn"
                        data-datetime="${slot.datetime}"
                        data-time="${slot.time}"
                        onclick="selectSlot(this)">
                    ${slot.time}
                </button>`).join('');
        }

        if (slotsSection) slotsSection.style.display = 'block';
        if (document.getElementById('booking-reason-section')) {
            document.getElementById('booking-reason-section').style.display = 'none';
        }

    } catch (e) {
        if (slotsLoading) slotsLoading.classList.add('d-none');
        console.error('Помилка завантаження слотів:', e);
    }
}

/**
 * Вибір часового слоту.
 */
function selectSlot(btn) {
    // Знімаємо виділення з усіх
    document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('selected', 'btn-primary'));
    document.querySelectorAll('.slot-btn').forEach(b => b.classList.add('btn-outline-primary'));

    // Виділяємо вибраний
    btn.classList.remove('btn-outline-primary');
    btn.classList.add('btn-primary', 'selected');

    selectedDateTime = btn.dataset.datetime;
    const dateInput = document.getElementById('booking-date');
    const dateStr = dateInput?.value;

    // Показуємо summary
    const summary = document.getElementById('booking-summary');
    const summaryText = document.getElementById('booking-summary-text');
    if (summary && summaryText) {
        const dateFormatted = new Date(dateStr).toLocaleDateString('uk-UA', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        });
        summaryText.textContent = `${dateFormatted} о ${btn.dataset.time}`;
        summary.classList.remove('d-none');
    }

    // Показуємо нотатки
    const notesSection = document.getElementById('booking-reason-section');
    if (notesSection) notesSection.style.display = 'block';

    // Активуємо кнопку запису
    const bookBtn = document.getElementById('book-btn');
    if (bookBtn) bookBtn.disabled = false;
}

/**
 * Створення запису на прийом.
 */
async function createAppointment() {
    if (!selectedDateTime) return;

    if (!isAuthenticated()) {
        window.location.href = '/login/';
        return;
    }

    const user = getCurrentUser();
    if (user && user.role !== 'patient') {
        alert('Запис доступний тільки для пацієнтів.');
        return;
    }

    const btn = document.getElementById('book-btn');
    const spinner = document.getElementById('book-spinner');
    const errorDiv = document.getElementById('booking-error');

    btn.disabled = true;
    if (spinner) spinner.classList.remove('d-none');
    errorDiv.classList.add('d-none');

    const reason = document.getElementById('booking-reason')?.value || '';

    try {
        const response = await apiRequest('/appointments/', {
            method: 'POST',
            body: JSON.stringify({
                doctor_id: DOCTOR_ID,
                date_time: selectedDateTime,
                reason,
            }),
        });

        const data = await response.json();

        if (response.ok) {
            // Успішний запис — показуємо повідомлення та редіректимо
            const modal = new bootstrap.Modal(document.createElement('div'));
            window.location.href = `/appointments/${data.id}/`;
        } else {
            const errors = Object.values(data).flat().join(' ');
            errorDiv.textContent = errors || 'Помилка запису. Спробуйте знову.';
            errorDiv.classList.remove('d-none');
        }
    } catch (e) {
        errorDiv.textContent = 'Помилка з\'єднання.';
        errorDiv.classList.remove('d-none');
    } finally {
        btn.disabled = false;
        if (spinner) spinner.classList.add('d-none');
    }
}

function showError(message) {
    document.getElementById('doctor-loader').innerHTML =
        `<div class="alert alert-danger">${message}</div>`;
}
