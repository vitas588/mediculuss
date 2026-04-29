/**
 * ============================================
 * Mediculus Hospital - Головна сторінка
 * ============================================
 */

document.addEventListener('DOMContentLoaded', async () => {
    handlePageMessages();
    await loadSpecialties();
    setupSearch();
    updateHeroStats();
});

/**
 * Показуємо alert-сповіщення залежно від query-параметра.
 */
function handlePageMessages() {
    const params = new URLSearchParams(window.location.search);
    const alertEl = document.getElementById('home-alert');
    const alertMsg = document.getElementById('home-alert-msg');
    if (!alertEl || !alertMsg) return;

    if (params.get('account_deleted') === '1') {
        alertMsg.textContent = 'Ваш акаунт успішно видалено. До побачення!';
        alertEl.classList.remove('d-none');
        // Очищуємо параметр з URL без перезавантаження
        history.replaceState(null, '', '/');
    }
}

/**
 * Завантаження та відображення спеціальностей.
 * ВИПРАВЛЕНО: API повертає paginated { count, results: [...] }, а не простий масив.
 */
async function loadSpecialties() {
    const grid = document.getElementById('specialties-grid');
    const heroSelect = document.getElementById('hero-specialty');
    if (!grid) return;

    try {
        const response = await fetch('/api/doctors/specialties/');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        // Підтримуємо обидва формати: paginated { results: [...] } та простий масив
        const specialties = Array.isArray(data) ? data : (data.results || []);

        if (specialties.length === 0) {
            grid.innerHTML = '<div class="col-12 text-center text-muted">Спеціальності не знайдено</div>';
            return;
        }

        // Заповнюємо сітку клікабельних іконок спеціальностей
        grid.innerHTML = specialties.map(s => `
            <div class="col-6 col-sm-4 col-md-3 col-lg-2">
                <div class="card border-0 shadow-sm specialty-card text-center p-3 h-100 cursor-pointer"
                     role="button"
                     tabindex="0"
                     onclick="window.location='/doctors/?specialty=${encodeURIComponent(s.slug)}'"
                     onkeypress="if(event.key==='Enter')window.location='/doctors/?specialty=${encodeURIComponent(s.slug)}'">
                    <span class="specialty-icon" aria-hidden="true">${s.icon || '🏥'}</span>
                    <p class="mb-0 fw-semibold small">${escapeHtml(s.name)}</p>
                </div>
            </div>`).join('');

        // Заповнюємо dropdown форми пошуку
        if (heroSelect) {
            heroSelect.innerHTML = '<option value="">Всі спеціальності</option>' +
                specialties.map(s =>
                    `<option value="${escapeHtml(s.slug)}">${s.icon || ''} ${escapeHtml(s.name)}</option>`
                ).join('');
        }

    } catch (e) {
        console.error('Помилка завантаження спеціальностей:', e);
        grid.innerHTML = `
            <div class="col-12 text-center text-muted py-3">
                <i class="bi bi-exclamation-circle me-2"></i>Не вдалось завантажити спеціальності
            </div>`;
    }
}

/**
 * Кнопка пошуку на hero секції.
 */
function setupSearch() {
    const btn = document.getElementById('hero-search-btn');
    const searchInput = document.getElementById('hero-search');
    const specialtySelect = document.getElementById('hero-specialty');

    if (!btn) return;

    const doSearch = () => {
        const params = new URLSearchParams();
        const search = searchInput?.value.trim();
        const specialty = specialtySelect?.value;
        if (search) params.set('search', search);
        if (specialty) params.set('specialty', specialty);
        window.location.href = `/doctors/?${params.toString()}`;
    };

    btn.addEventListener('click', doSearch);
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') doSearch(); });
    }
}

/**
 * Оновлення статистики в hero секції:
 * - кількість лікарів
 * - реальна кількість завершених записів (замість статичних "42")
 */
async function updateHeroStats() {
    // Кількість лікарів
    const doctorsCountEl = document.getElementById('hero-doctors-count');
    if (doctorsCountEl) {
        try {
            const resp = await fetch('/api/doctors/');
            if (resp.ok) {
                const data = await resp.json();
                doctorsCountEl.textContent = data.count ?? (Array.isArray(data) ? data.length : '—');
            }
        } catch { doctorsCountEl.textContent = '—'; }
    }

    // ВИПРАВЛЕНО: реальна кількість завершених записів
    const completedEl = document.getElementById('hero-completed-count');
    if (completedEl) {
        try {
            const resp = await fetch('/api/appointments/public-stats/');
            if (resp.ok) {
                const stats = await resp.json();
                completedEl.textContent = stats.completed_total ?? '—';
            }
        } catch { completedEl.textContent = '—'; }
    }
}
