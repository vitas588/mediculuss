/**
 * ============================================
 * Mediculus Hospital - Мої записи (пацієнт)
 * ============================================
 */

let currentStatus = 'all';
let allAppointments = [];
let displayedCount = 0;
const PAGE_SIZE = 10;

document.addEventListener('DOMContentLoaded', async () => {
    if (!isAuthenticated()) {
        window.location.href = '/login/';
        return;
    }

    const params = new URLSearchParams(window.location.search);
    currentStatus = params.get('status') || 'all';
    setActiveTab(currentStatus);

    // Вкладки статусу
    document.querySelectorAll('[data-status]').forEach(btn => {
        btn.addEventListener('click', () => {
            currentStatus = btn.dataset.status;
            setActiveTab(currentStatus);
            renderFiltered();
        });
    });

    // Фільтр за діапазоном дат
    setupDateRangeFilter();

    // Кнопка "Завантажити ще"
    document.getElementById('load-more-btn')?.addEventListener('click', loadMore);

    await autoCancelExpired();
    await loadAppointments();
});

async function autoCancelExpired() {
    try {
        const user = getCurrentUser();
        if (!user || user.role !== 'patient') return;
        await apiRequest('/appointments/auto-cancel/', { method: 'POST' });
    } catch (e) {}
}

function setActiveTab(status) {
    document.querySelectorAll('[data-status]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.status === status);
    });
}

function setupDateRangeFilter() {
    const rangeSelect = document.getElementById('date-range-filter');
    const fromCol = document.getElementById('date-from-col');
    const toCol = document.getElementById('date-to-col');

    rangeSelect?.addEventListener('change', () => {
        if (rangeSelect.value === 'custom') {
            fromCol?.classList.remove('d-none');
            toCol?.classList.remove('d-none');
        } else {
            fromCol?.classList.add('d-none');
            toCol?.classList.add('d-none');
        }
        renderFiltered();
    });

    document.getElementById('date-from')?.addEventListener('change', renderFiltered);
    document.getElementById('date-to')?.addEventListener('change', renderFiltered);
}

async function loadAppointments() {
    const container = document.getElementById('appointments-list');
    if (!container) return;

    container.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status"></div>
        </div>`;

    try {
        const response = await apiRequest('/appointments/');
        if (!response) return;
        const data = await response.json();
        allAppointments = data.results || (Array.isArray(data) ? data : []);
        renderFiltered();
    } catch (e) {
        container.innerHTML = '<div class="alert alert-danger">Помилка завантаження записів.</div>';
    }
}

function getFilteredAppointments() {
    let filtered = allAppointments;

    // Фільтр за статусом
    if (currentStatus !== 'all') {
        filtered = filtered.filter(a => a.status === currentStatus);
    }

    // Фільтр за діапазоном дат
    const rangeVal = document.getElementById('date-range-filter')?.value || 'all';
    if (rangeVal !== 'all') {
        const now = new Date();
        if (rangeVal === 'custom') {
            const from = document.getElementById('date-from')?.value;
            const to = document.getElementById('date-to')?.value;
            if (from) filtered = filtered.filter(a => new Date(a.date_time) >= new Date(from));
            if (to) {
                const toEnd = new Date(to);
                toEnd.setHours(23, 59, 59);
                filtered = filtered.filter(a => new Date(a.date_time) <= toEnd);
            }
        } else {
            const days = parseInt(rangeVal);
            const since = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
            filtered = filtered.filter(a => new Date(a.date_time) >= since);
        }
    }

    return filtered;
}

function renderFiltered() {
    displayedCount = 0;
    const container = document.getElementById('appointments-list');
    if (!container) return;

    const filtered = getFilteredAppointments();

    if (filtered.length === 0) {
        container.innerHTML = renderEmptyState();
        document.getElementById('load-more-container')?.classList.add('d-none');
        return;
    }

    const toShow = filtered.slice(0, PAGE_SIZE);
    displayedCount = toShow.length;
    container.innerHTML = toShow.map(renderAppointmentCard).join('');
    setupCancelButtons();

    // Показати/сховати кнопку "Завантажити ще"
    const loadMoreContainer = document.getElementById('load-more-container');
    if (loadMoreContainer) {
        loadMoreContainer.classList.toggle('d-none', displayedCount >= filtered.length);
    }
}

function loadMore() {
    const container = document.getElementById('appointments-list');
    if (!container) return;

    const filtered = getFilteredAppointments();
    const nextBatch = filtered.slice(displayedCount, displayedCount + PAGE_SIZE);
    displayedCount += nextBatch.length;

    container.insertAdjacentHTML('beforeend', nextBatch.map(renderAppointmentCard).join(''));
    setupCancelButtons();

    const loadMoreContainer = document.getElementById('load-more-container');
    if (loadMoreContainer) {
        loadMoreContainer.classList.toggle('d-none', displayedCount >= filtered.length);
    }
}

/**
 * Розширена картка запису.
 */
function renderAppointmentCard(apt) {
    const statusMap = {
        planned:   { class: 'status-planned',   icon: 'clock',              text: 'Заплановано' },
        completed: { class: 'status-completed', icon: 'check-circle',       text: 'Завершено' },
        cancelled: { class: 'status-cancelled', icon: 'x-circle',           text: 'Скасовано' },
        missed:    { class: 'status-missed',    icon: 'exclamation-circle', text: 'Пропущено' },
    };
    const statusInfo = statusMap[apt.status] || statusMap.planned;

    const dateTime = new Date(apt.date_time);
    const dateFormatted = dateTime.toLocaleDateString('uk-UA', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
    const timeStart = dateTime.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
    const endTime = new Date(dateTime.getTime() + (apt.slot_duration || 30) * 60000);
    const timeEnd = endTime.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });

    const photoHtml = apt.doctor_photo_url
        ? `<img src="${apt.doctor_photo_url}" class="rounded-circle me-3" style="width:48px;height:48px;object-fit:cover" alt=""
               onerror="this.outerHTML='<div class=\\'doctor-avatar-placeholder me-3\\' style=\\'width:48px;height:48px;font-size:1.2rem\\'><i class=\\'bi bi-person-fill\\'></i></div>'">`
        : `<div class="doctor-avatar-placeholder me-3" style="width:48px;height:48px;font-size:1.2rem"><i class="bi bi-person-fill"></i></div>`;

    return `
        <div class="card border-0 shadow-sm appointment-card mb-3">
            <div class="card-body p-4">
                <div class="row align-items-center">
                    <div class="col-md-6">
                        <div class="d-flex align-items-center">
                            ${photoHtml}
                            <div>
                                <h6 class="fw-bold mb-1">
                                    <a href="/doctors/${apt.doctor_id}/" class="text-decoration-none text-dark">${escapeHtml(apt.doctor_name)}</a>
                                </h6>
                                <p class="text-muted small mb-1">${escapeHtml(apt.specialty_name || '')}</p>
                                <p class="mb-0 small text-muted">
                                    <i class="bi bi-calendar3 me-1"></i>${dateFormatted}
                                </p>
                                <p class="mb-0 small text-muted">
                                    <i class="bi bi-clock me-1"></i>${timeStart} – ${timeEnd}
                                </p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-2 mt-2 mt-md-0">
                        <div class="d-flex align-items-center gap-1 flex-wrap">
                            <span class="badge px-2 py-2 ${statusInfo.class}">
                                <i class="bi bi-${statusInfo.icon} me-1"></i>${statusInfo.text}
                            </span>
                            ${apt.has_medical_record ? `
                                <span class="badge bg-success-soft text-success" title="Є результати прийому">
                                    <i class="bi bi-file-medical"></i>
                                </span>` : ''}
                        </div>
                    </div>
                    <div class="col-md-4 mt-2 mt-md-0 d-flex gap-1 justify-content-md-end flex-nowrap appointment-actions"
                         style="font-size:0.78rem; white-space:nowrap">
                        <a href="/appointments/${apt.id}/" class="btn btn-outline-primary btn-sm">
                            <i class="bi bi-eye me-1"></i>Переглянути
                        </a>
                        ${apt.status === 'planned' ? `
                            <button class="btn btn-outline-danger btn-sm cancel-btn" data-id="${apt.id}">
                                <i class="bi bi-x me-1"></i>Скасувати
                            </button>` : ''}
                        <a href="/doctors/${apt.doctor_id}/" class="btn btn-outline-secondary btn-sm">
                            <i class="bi bi-plus-circle me-1"></i>Записатися ще раз
                        </a>
                    </div>
                </div>
            </div>
        </div>`;
}

function renderEmptyState() {
    const messages = {
        all: 'У вас ще немає жодного запису до лікаря.',
        planned: 'У вас немає запланованих записів.',
        completed: 'У вас немає завершених записів.',
        cancelled: 'У вас немає скасованих записів.',
        missed: 'У вас немає пропущених записів.',
    };
    return `
        <div class="text-center py-5">
            <i class="bi bi-calendar-x text-muted" style="font-size:3rem"></i>
            <h5 class="mt-3 text-muted">${messages[currentStatus] || messages.all}</h5>
            <a href="/doctors/" class="btn btn-primary mt-3">
                <i class="bi bi-search me-1"></i>Знайти лікаря
            </a>
        </div>`;
}

function setupCancelButtons() {
    document.querySelectorAll('.cancel-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const id = btn.dataset.id;
            if (!confirm('Ви впевнені що хочете скасувати цей запис?')) return;

            btn.disabled = true;
            btn.innerHTML = '<div class="spinner-border spinner-border-sm"></div>';

            try {
                const response = await apiRequest(`/appointments/${id}/cancel/`, { method: 'PATCH' });
                if (response && response.ok) {
                    await loadAppointments();
                } else {
                    const data = await response?.json();
                    alert(data?.error || 'Помилка скасування.');
                    btn.disabled = false;
                    btn.innerHTML = '<i class="bi bi-x me-1"></i>Скасувати';
                }
            } catch (e) {
                alert('Помилка з\'єднання.');
                btn.disabled = false;
            }
        });
    });
}
