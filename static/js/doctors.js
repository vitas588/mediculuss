/**
 * ============================================
 * Mediculus Hospital - Список лікарів
 * ============================================
 */

function getYearsWord(years) {
    const lastTwo = years % 100;
    const lastOne = years % 10;
    if (lastTwo >= 11 && lastTwo <= 19) return 'років';
    if (lastOne === 1) return 'рік';
    if (lastOne >= 2 && lastOne <= 4) return 'роки';
    return 'років';
}

let currentSearch = '';
let currentSpecialty = '';
let nextPageUrl = null;

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    currentSearch = params.get('search') || '';
    currentSpecialty = params.get('specialty') || '';

    const searchInput = document.getElementById('search-input');
    const specialtyFilter = document.getElementById('specialty-filter');
    if (searchInput) searchInput.value = currentSearch;
    if (specialtyFilter) specialtyFilter.value = currentSpecialty;

    loadDoctors();
    setupFilters();

    document.getElementById('load-more-btn')?.addEventListener('click', loadMore);
});

async function loadDoctors() {
    const grid = document.getElementById('doctors-grid');
    const countEl = document.getElementById('results-count');
    const noResults = document.getElementById('no-results');
    if (!grid) return;

    showSkeleton(grid);
    if (noResults) noResults.classList.add('d-none');
    document.getElementById('load-more-container')?.classList.add('d-none');
    nextPageUrl = null;

    try {
        const params = new URLSearchParams();
        if (currentSearch) params.set('search', currentSearch);
        if (currentSpecialty) params.set('specialty', currentSpecialty);

        const response = await fetch(`/api/doctors/?${params.toString()}`);
        const data = await response.json();

        const doctors = data.results || (Array.isArray(data) ? data : []);
        const total = data.count || doctors.length;
        nextPageUrl = data.next || null;

        if (countEl) countEl.textContent = `Знайдено: ${total} лікар(ів)`;

        if (doctors.length === 0) {
            grid.innerHTML = '';
            if (noResults) noResults.classList.remove('d-none');
            return;
        }

        grid.innerHTML = doctors.map(renderDoctorCard).join('');

        const loadMoreContainer = document.getElementById('load-more-container');
        if (loadMoreContainer) {
            loadMoreContainer.classList.toggle('d-none', !nextPageUrl);
        }
    } catch (e) {
        console.error('Помилка завантаження лікарів:', e);
        grid.innerHTML = '<div class="col-12 text-center text-danger">Помилка завантаження</div>';
    }
}

async function loadMore() {
    if (!nextPageUrl) return;

    const grid = document.getElementById('doctors-grid');
    const loadMoreBtn = document.getElementById('load-more-btn');
    if (!grid) return;

    if (loadMoreBtn) {
        loadMoreBtn.disabled = true;
        loadMoreBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Завантаження...';
    }

    try {
        const response = await fetch(nextPageUrl);
        const data = await response.json();

        const doctors = data.results || [];
        nextPageUrl = data.next || null;

        grid.insertAdjacentHTML('beforeend', doctors.map(renderDoctorCard).join(''));

        const loadMoreContainer = document.getElementById('load-more-container');
        if (loadMoreContainer) {
            loadMoreContainer.classList.toggle('d-none', !nextPageUrl);
        }
    } catch (e) {
        console.error('Помилка завантаження:', e);
    } finally {
        if (loadMoreBtn) {
            loadMoreBtn.disabled = false;
            loadMoreBtn.innerHTML = '<i class="bi bi-arrow-down-circle me-1"></i>Завантажити ще';
        }
    }
}

function renderDoctorCard(doctor) {
    const photoHtml = doctor.photo_url
        ? `<img src="${doctor.photo_url}" class="doctor-avatar" alt="${escapeHtml(doctor.full_name)}"
               onerror="this.outerHTML='<div class=\\'doctor-avatar-placeholder\\'><i class=\\'bi bi-person-fill\\'></i></div>'">`
        : `<div class="doctor-avatar-placeholder"><i class="bi bi-person-fill"></i></div>`;

    return `
        <div class="col-md-6 col-lg-4">
            <div class="card border-0 shadow-sm doctor-card h-100">
                <div class="card-body p-4">
                    <div class="d-flex align-items-start mb-3">
                        ${photoHtml}
                        <div class="ms-3 flex-grow-1 overflow-hidden">
                            <h6 class="fw-bold mb-0 text-truncate">${escapeHtml(doctor.full_name)}</h6>
                            <span class="text-muted small">
                                ${doctor.specialty_icon || '🏥'} ${escapeHtml(doctor.specialty_name || '—')}
                            </span>
                        </div>
                    </div>

                    <div class="d-flex gap-3 mb-3 small text-muted">
                        <span>
                            <i class="bi bi-briefcase me-1"></i>${doctor.experience_years} ${getYearsWord(doctor.experience_years)} досвіду
                        </span>
                        <span>
                            <i class="bi bi-clock me-1"></i>${doctor.slot_duration} хв
                        </span>
                    </div>

                    <div class="d-flex gap-2">
                        <a href="/doctors/${doctor.id}/" class="btn btn-primary btn-sm flex-grow-1">
                            <i class="bi bi-calendar-plus me-1"></i>Записатись
                        </a>
                    </div>
                </div>
            </div>
        </div>`;
}

function showSkeleton(container) {
    container.innerHTML = Array(6).fill(`
        <div class="col-md-6 col-lg-4">
            <div class="card border-0 shadow-sm h-100">
                <div class="card-body p-4">
                    <div class="d-flex align-items-center mb-3">
                        <div class="skeleton-circle me-3"></div>
                        <div class="flex-grow-1">
                            <div class="skeleton-line w-75 mb-1"></div>
                            <div class="skeleton-line w-50"></div>
                        </div>
                    </div>
                    <div class="skeleton-line w-100 mb-1"></div>
                    <div class="skeleton-line w-60"></div>
                </div>
            </div>
        </div>`).join('');
}

function setupFilters() {
    const searchInput = document.getElementById('search-input');
    const specialtyFilter = document.getElementById('specialty-filter');
    const searchBtn = document.getElementById('search-btn');
    const resetBtn = document.getElementById('reset-btn');
    const resetBtn2 = document.getElementById('reset-btn-2');

    const doSearch = () => {
        currentSearch = searchInput?.value.trim() || '';
        currentSpecialty = specialtyFilter?.value || '';

        const params = new URLSearchParams();
        if (currentSearch) params.set('search', currentSearch);
        if (currentSpecialty) params.set('specialty', currentSpecialty);
        history.replaceState(null, '', `/doctors/?${params.toString()}`);

        loadDoctors();
    };

    const doReset = () => {
        if (searchInput) searchInput.value = '';
        if (specialtyFilter) specialtyFilter.value = '';
        currentSearch = '';
        currentSpecialty = '';
        history.replaceState(null, '', '/doctors/');
        loadDoctors();
    };

    if (searchBtn) searchBtn.addEventListener('click', doSearch);
    if (resetBtn) resetBtn.addEventListener('click', doReset);
    if (resetBtn2) resetBtn2.addEventListener('click', doReset);

    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') doSearch();
        });
    }

    if (specialtyFilter) {
        specialtyFilter.addEventListener('change', doSearch);
    }
}
