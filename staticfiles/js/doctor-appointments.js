/**
 * ============================================
 * Mediculus Hospital - Записи лікаря
 * ============================================
 */

let currentStatus = 'all';
let allAppointments = [];
let displayedCount = 0;
const PAGE_SIZE = 10;
let _appointmentsTimer = null;

document.addEventListener('DOMContentLoaded', async () => {
    if (!isAuthenticated()) {
        window.location.href = '/login/';
        return;
    }

    const user = getCurrentUser();
    if (!user || user.role !== 'doctor') {
        window.location.href = '/';
        return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const statusParam = urlParams.get('status');
    if (statusParam && ['planned', 'completed', 'cancelled', 'missed'].includes(statusParam)) {
        currentStatus = statusParam;
    }

    // Якщо передано ?date=YYYY-MM-DD — встановлюємо custom-фільтр по цій даті
    const dateParam = urlParams.get('date');
    if (dateParam) {
        const rangeSelect = document.getElementById('date-range-filter');
        const fromInput = document.getElementById('date-from');
        const toInput = document.getElementById('date-to');
        const fromCol = document.getElementById('date-from-col');
        const toCol = document.getElementById('date-to-col');
        if (rangeSelect) rangeSelect.value = 'custom';
        if (fromInput) fromInput.value = dateParam;
        if (toInput) toInput.value = dateParam;
        if (fromCol) fromCol.classList.remove('d-none');
        if (toCol) toCol.classList.remove('d-none');
    }

    // Вкладки статусу
    document.querySelectorAll('[data-status]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.status === currentStatus);
        btn.addEventListener('click', () => {
            currentStatus = btn.dataset.status;
            document.querySelectorAll('[data-status]').forEach(b => b.classList.toggle('active', b.dataset.status === currentStatus));
            renderFiltered();
        });
    });

    document.getElementById('search-patient')?.addEventListener('input', renderFiltered);
    setupDateRangeFilter();

    document.getElementById('reset-filters-btn')?.addEventListener('click', () => {
        const searchInput = document.getElementById('search-patient');
        const rangeSelect = document.getElementById('date-range-filter');
        if (searchInput) searchInput.value = '';
        if (rangeSelect) rangeSelect.value = 'all';
        document.getElementById('date-from-col')?.classList.add('d-none');
        document.getElementById('date-to-col')?.classList.add('d-none');
        document.getElementById('date-from') && (document.getElementById('date-from').value = '');
        document.getElementById('date-to') && (document.getElementById('date-to').value = '');
        renderFiltered();
    });

    document.getElementById('load-more-btn')?.addEventListener('click', loadMore);

    await autoCancelDoctor();
    await loadDoctorAppointments();
});

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

async function autoCancelDoctor() {
    try {
        await apiRequest('/appointments/auto-cancel-doctor/', { method: 'POST' });
    } catch (e) {}
}

async function loadDoctorAppointments() {
    const container = document.getElementById('doctor-appointments-list');
    if (!container) return;

    container.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>';

    try {
        const response = await apiRequest('/appointments/');
        if (!response) return;
        const data = await response.json();
        allAppointments = data.results || (Array.isArray(data) ? data : []);
        renderFiltered();
    } catch (e) {
        container.innerHTML = '<div class="alert alert-danger">Помилка завантаження.</div>';
    }
}

function getFilteredAppointments() {
    let filtered = allAppointments;

    // Статус
    if (currentStatus !== 'all') {
        filtered = filtered.filter(a => a.status === currentStatus);
    }

    // Пошук за пацієнтом
    const searchVal = (document.getElementById('search-patient')?.value || '').toLowerCase().trim();
    if (searchVal) {
        filtered = filtered.filter(a => (a.patient_name || '').toLowerCase().includes(searchVal));
    }

    // Діапазон дат
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
    const container = document.getElementById('doctor-appointments-list');
    if (!container) return;

    const filtered = getFilteredAppointments();

    if (filtered.length === 0) {
        container.innerHTML = `<div class="text-center py-5">
            <i class="bi bi-calendar-x text-muted fs-1 d-block mb-2"></i>
            <p class="text-muted">Записів не знайдено</p>
        </div>`;
        document.getElementById('load-more-container')?.classList.add('d-none');
        return;
    }

    const toShow = filtered.slice(0, PAGE_SIZE);
    displayedCount = toShow.length;
    container.innerHTML = toShow.map(renderDoctorAppointmentCard).join('');
    setupCompleteQuickButtons();
    startCompleteQuickTimer();

    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });

    const loadMoreContainer = document.getElementById('load-more-container');
    if (loadMoreContainer) {
        loadMoreContainer.classList.toggle('d-none', displayedCount >= filtered.length);
    }
}

function loadMore() {
    const container = document.getElementById('doctor-appointments-list');
    if (!container) return;

    const filtered = getFilteredAppointments();
    const nextBatch = filtered.slice(displayedCount, displayedCount + PAGE_SIZE);
    displayedCount += nextBatch.length;

    container.insertAdjacentHTML('beforeend', nextBatch.map(renderDoctorAppointmentCard).join(''));
    setupCompleteQuickButtons();

    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });

    const loadMoreContainer = document.getElementById('load-more-container');
    if (loadMoreContainer) {
        loadMoreContainer.classList.toggle('d-none', displayedCount >= filtered.length);
    }
}

function renderDoctorAppointmentCard(apt) {
    const dt = new Date(apt.date_time);
    const dateFormatted = dt.toLocaleDateString('uk-UA', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
    const timeStart = dt.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
    const endTime = new Date(dt.getTime() + (apt.slot_duration || 30) * 60000);
    const timeEnd = endTime.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });

    const statusMap = {
        planned:   { class: 'status-planned',   text: 'Заплановано' },
        completed: { class: 'status-completed', text: 'Завершено' },
        cancelled: { class: 'status-cancelled', text: 'Скасовано' },
        missed:    { class: 'status-missed',    text: 'Пропущено' },
    };
    const statusInfo = statusMap[apt.status] || statusMap.planned;

    // Кнопка "Завершити"
    let completeBtn = '';
    if (apt.status === 'planned') {
        const now = new Date();
        if (dt <= now) {
            completeBtn = `
                <button class="btn btn-sm btn-success complete-quick-btn"
                        data-id="${apt.id}"
                        data-patient="${escapeHtml(apt.patient_name)}">
                    <i class="bi bi-check-circle me-1"></i>Завершити
                </button>`;
        } else {
            completeBtn = `
                <span data-bs-toggle="tooltip" title="Прийом ще не розпочався" tabindex="0"
                      data-apt-time="${apt.date_time}" data-apt-id="${apt.id}">
                    <button class="btn btn-sm btn-success" disabled style="pointer-events:none;">
                        <i class="bi bi-check-circle me-1"></i>Завершити
                    </button>
                </span>`;
        }
    }

    return `
        <div class="card border-0 shadow-sm mb-3">
            <div class="card-body p-4">
                <div class="row align-items-center">
                    <div class="col-md-5">
                        <div class="d-flex align-items-center">
                            <div class="rounded-circle bg-primary-soft d-flex align-items-center justify-content-center me-3 flex-shrink-0"
                                 style="width:48px;height:48px;font-size:1.2rem;">
                                <i class="bi bi-person text-primary"></i>
                            </div>
                            <div>
                                <h6 class="fw-bold mb-1">${escapeHtml(apt.patient_name)}</h6>
                                <p class="text-muted small mb-0">
                                    <i class="bi bi-calendar3 me-1"></i>${dateFormatted}
                                </p>
                                <p class="text-muted small mb-0">
                                    <i class="bi bi-clock me-1"></i>${timeStart} – ${timeEnd}
                                </p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mt-2 mt-md-0">
                        <span class="badge px-3 py-2 ${statusInfo.class}">
                            ${statusInfo.text}
                        </span>
                    </div>
                    <div class="col-md-4 mt-2 mt-md-0 d-flex gap-2 justify-content-md-end">
                        <a href="/appointments/${apt.id}/" class="btn btn-sm btn-outline-primary">
                            <i class="bi bi-eye me-1"></i>Переглянути прийом
                        </a>
                        ${completeBtn}
                    </div>
                </div>
            </div>
        </div>`;
}

function setupCompleteQuickButtons() {
    document.querySelectorAll('.complete-quick-btn:not([data-handler])').forEach(btn => {
        btn.dataset.handler = '1';
        btn.addEventListener('click', () => {
            window.location.href = `/appointments/${btn.dataset.id}/`;
        });
    });
}

/**
 * Автоматична активація кнопок "Завершити" коли час прийому настав.
 */
function startCompleteQuickTimer() {
    if (_appointmentsTimer) clearInterval(_appointmentsTimer);
    _appointmentsTimer = setInterval(() => {
        const now = new Date();
        document.querySelectorAll('[data-apt-time]').forEach(span => {
            if (new Date(span.dataset.aptTime) <= now) {
                const id = span.dataset.aptId;
                const tooltipInstance = bootstrap.Tooltip.getInstance(span);
                if (tooltipInstance) tooltipInstance.dispose();
                const btn = document.createElement('button');
                btn.className = 'btn btn-sm btn-success complete-quick-btn';
                btn.dataset.id = id;
                btn.innerHTML = '<i class="bi bi-check-circle me-1"></i>Завершити';
                span.replaceWith(btn);
                setupCompleteQuickButtons();
            }
        });
    }, 30000);
}
