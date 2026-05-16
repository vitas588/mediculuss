/**
 * ============================================
 * Mediculus Hospital - Сповіщення (Notifications)
 * ============================================
 * Завантаження та відображення сповіщень у навбарі.
 */

/**
 * Завантажити сповіщення та оновити UI.
 */
async function loadNotifications() {
    if (!isAuthenticated()) return;

    try {
        const response = await apiRequest('/notifications/');
        if (!response || !response.ok) return;

        const data = await response.json();
        updateNotificationBadge(data.unread_count);
        renderNotifications(data.notifications);
    } catch (e) {
        console.error('Помилка завантаження сповіщень:', e);
    }
}

/**
 * Оновити лічильник непрочитаних сповіщень.
 */
function updateNotificationBadge(count) {
    const badge = document.getElementById('notif-badge');
    if (!badge) return;

    if (count > 0) {
        badge.textContent = count > 9 ? '9+' : count;
        badge.classList.remove('d-none');
    } else {
        badge.classList.add('d-none');
    }
}

/**
 * Відрендерити список сповіщень в офканвасі.
 */
function renderNotifications(notifications) {
    const container = document.getElementById('notifications-list');
    if (!container) return;

    if (!notifications || notifications.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="bi bi-bell-slash fs-1 d-block mb-2"></i>
                Немає сповіщень
            </div>`;
        return;
    }

    container.innerHTML = notifications.map(n => `
        <div class="notification-item ${!n.is_read ? 'unread' : ''}"
             data-id="${n.id}" onclick="markNotificationRead(${n.id}, '${n.link || ''}')">
            <div class="d-flex gap-2 align-items-start">
                <i class="bi bi-${n.is_read ? 'bell' : 'bell-fill'} text-primary mt-1 flex-shrink-0"></i>
                <div class="flex-grow-1 overflow-hidden">
                    <p class="mb-1 small ${!n.is_read ? 'fw-semibold' : ''}">${escapeHtml(n.message)}</p>
                    <small class="text-muted">${n.time_ago}</small>
                </div>
                ${!n.is_read ? '<span class="badge bg-primary rounded-pill ms-auto">Нове</span>' : ''}
            </div>
        </div>`).join('');
}

/**
 * Позначити сповіщення як прочитане та перейти за посиланням.
 */
async function markNotificationRead(id, link) {
    try {
        await apiRequest(`/notifications/${id}/read/`, { method: 'PATCH' });
        // Оновлюємо UI
        const item = document.querySelector(`[data-id="${id}"]`);
        if (item) item.classList.remove('unread');
        // Зменшуємо лічильник
        const badge = document.getElementById('notif-badge');
        if (badge) {
            const count = parseInt(badge.textContent) - 1;
            if (count <= 0) {
                badge.classList.add('d-none');
            } else {
                badge.textContent = count;
            }
        }
    } catch (e) {
        console.error('Помилка:', e);
    }

    // Переходимо за посиланням
    if (link && link !== 'undefined') {
        window.location.href = link;
    }
}

/**
 * Позначити всі сповіщення як прочитані.
 */
async function markAllRead() {
    try {
        const response = await apiRequest('/notifications/read-all/', { method: 'PATCH' });
        if (response && response.ok) {
            await loadNotifications();
        }
    } catch (e) {
        console.error('Помилка:', e);
    }
}

/**
 * Екранування HTML (захист від XSS).
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

// ---- Ініціалізація ----
document.addEventListener('DOMContentLoaded', () => {
    // Завантаження сповіщень при відкритті офканвасу
    const offcanvasEl = document.getElementById('notificationsOffcanvas');
    if (offcanvasEl) {
        offcanvasEl.addEventListener('show.bs.offcanvas', loadNotifications);
    }

    // Кнопка "позначити всі як прочитані"
    const markAllBtn = document.getElementById('mark-all-read');
    if (markAllBtn) {
        markAllBtn.addEventListener('click', markAllRead);
    }

    // Перевіряємо лічильник одразу при завантаженні сторінки
    if (isAuthenticated()) {
        loadNotifications();
    }
});
