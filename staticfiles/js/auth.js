/**
 * ============================================
 * Mediculus Hospital - Утиліти авторизації
 * ============================================
 * Глобальні функції для роботи з JWT токенами.
 * Завантажується на кожній сторінці через base.html.
 */

// ---- Константи ----
const API_BASE = '/api';
const TOKEN_KEY = 'mediculus_access_token';
const REFRESH_KEY = 'mediculus_refresh_token';
const USER_KEY = 'mediculus_user';

/**
 * Отримати access токен з localStorage.
 */
function getAccessToken() {
    return localStorage.getItem(TOKEN_KEY);
}

/**
 * Отримати refresh токен.
 */
function getRefreshToken() {
    return localStorage.getItem(REFRESH_KEY);
}

/**
 * Зберегти токени та дані користувача.
 */
function saveTokens(accessToken, refreshToken, user) {
    localStorage.setItem(TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_KEY, refreshToken);
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/**
 * Отримати дані поточного користувача.
 */
function getCurrentUser() {
    const data = localStorage.getItem(USER_KEY);
    return data ? JSON.parse(data) : null;
}

/**
 * Перевірити, чи авторизований користувач.
 */
function isAuthenticated() {
    return Boolean(getAccessToken());
}

/**
 * Видалити всі дані авторизації.
 */
function clearAuth() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
}

/**
 * Надіслати API запит з автоматичною авторизацією.
 * Автоматично оновлює токен якщо він застарів.
 */
async function apiRequest(url, options = {}) {
    const token = getAccessToken();

    const defaultHeaders = {
        'Content-Type': 'application/json',
    };
    if (token) {
        defaultHeaders['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...(options.headers || {}),
        },
    };

    let response = await fetch(`${API_BASE}${url}`, config);

    // Якщо токен застарів — намагаємося оновити
    if (response.status === 401 && getRefreshToken()) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
            config.headers['Authorization'] = `Bearer ${getAccessToken()}`;
            response = await fetch(`${API_BASE}${url}`, config);
        } else {
            // Refresh не вдався — виходимо
            clearAuth();
            window.location.href = '/login/';
            return null;
        }
    }

    return response;
}

/**
 * Оновити access токен через refresh токен.
 */
async function refreshAccessToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;

    try {
        const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh: refreshToken }),
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem(TOKEN_KEY, data.access);
            if (data.refresh) localStorage.setItem(REFRESH_KEY, data.refresh);
            return true;
        }
    } catch (e) {
        console.error('Помилка оновлення токена:', e);
    }

    return false;
}

/**
 * Вихід з системи.
 */
async function logout() {
    const refreshToken = getRefreshToken();

    try {
        if (refreshToken) {
            await apiRequest('/auth/logout/', {
                method: 'POST',
                body: JSON.stringify({ refresh: refreshToken }),
            });
        }
    } catch (e) {
        // Навіть якщо запит не вдався — очищаємо локально
    }

    clearAuth();
    window.location.href = '/';
}

/**
 * Оновлення UI навбару залежно від стану авторизації.
 */
function updateNavbar() {
    const user = getCurrentUser();
    const loginBtn = document.getElementById('nav-login');
    const registerBtn = document.getElementById('nav-register');
    const userMenu = document.getElementById('nav-user-menu');
    const userName = document.getElementById('nav-user-name');
    const cabinetBtn = document.getElementById('nav-cabinet-btn');

    if (user && isAuthenticated()) {
        // Приховуємо кнопки входу/реєстрації
        if (loginBtn) loginBtn.classList.add('d-none');
        if (registerBtn) registerBtn.classList.add('d-none');

        // Показуємо меню користувача
        if (userMenu) userMenu.classList.remove('d-none');

        if (user.role === 'doctor') {
            // Лікар: текстові лінки ліворуч; "Кабінет лікаря" — синя кнопка праворуч
            document.getElementById('nav-doctor-profile-li')?.classList.remove('d-none');
            document.getElementById('nav-doctor-patients-li')?.classList.remove('d-none');
            if (cabinetBtn) {
                cabinetBtn.classList.remove('d-none');
                cabinetBtn.href = '/doctors/cabinet/';
                cabinetBtn.title = 'Кабінет лікаря';
                if (userName) userName.textContent = 'Кабінет лікаря';
            }
        } else if (user.role === 'admin' || user.is_staff) {
            // Адмін: синя кнопка → панель статистики
            if (cabinetBtn) {
                cabinetBtn.classList.remove('d-none');
                cabinetBtn.href = '/admin-panel/';
                cabinetBtn.title = 'Панель статистики';
                if (userName) userName.textContent = 'Панель статистики';
            }
        } else {
            // Пацієнт: "Мої записи" — текстовий лінк ліворуч; синя кнопка → профіль
            document.getElementById('nav-appointments-link-li')?.classList.remove('d-none');
            if (cabinetBtn) {
                cabinetBtn.classList.remove('d-none');
                cabinetBtn.href = '/profile/';
                cabinetBtn.title = 'Мій кабінет';
                if (userName) userName.textContent = 'Мій кабінет';
            }
        }
    } else {
        // Показуємо кнопки авторизації
        if (loginBtn) loginBtn.classList.remove('d-none');
        if (registerBtn) registerBtn.classList.remove('d-none');
        if (userMenu) userMenu.classList.add('d-none');
    }
}

// ---- Обробники подій ----

// Вихід
document.addEventListener('DOMContentLoaded', () => {
    const logoutBtn = document.getElementById('nav-logout');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            logout();
        });
    }

    // Кнопка сповіщень
    const notifBtn = document.getElementById('nav-notifications-btn');
    if (notifBtn) {
        notifBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const offcanvas = new bootstrap.Offcanvas(
                document.getElementById('notificationsOffcanvas')
            );
            offcanvas.show();
        });
    }

    // Оновлення навбару
    updateNavbar();
});
