/**
 * ============================================
 * Mediculus — Панель доступності
 * ============================================
 * Фіксована кнопка ♿ / ↑ + offcanvas-панель:
 *   • Розмір шрифту: Менший(0.75) / Звичайний(1.0) / Більший(1.25) / Найбільший(1.5)
 *   • Контрастність (звична / висока)
 *   • Шрифт (звичайний / для дислексиків)
 *
 * Налаштування зберігаються в localStorage і
 * автоматично застосовуються при завантаженні сторінки.
 */

(function () {
    'use strict';

    const STORAGE_KEY = 'mediculus_a11y';
    const DEFAULT = { fontScale: 1.0, contrast: 'normal', font: 'normal' };

    /* ── Збереження / завантаження ──────────────────────── */
    function load() {
        try {
            return Object.assign({}, DEFAULT, JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'));
        } catch (_) {
            return Object.assign({}, DEFAULT);
        }
    }

    function save(s) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    }

    /* ── Текстові мітки масштабу ────────────────────────── */
    const SCALE_LABELS = {
        0.75: 'Менший',
        1.0:  'Звичайний',
        1.25: 'Більший',
        1.5:  'Найбільший'
    };

    function getScaleLabel(scale) {
        // Округлюємо до 2 знаків щоб уникнути float-похибок (1.0000001 тощо)
        var rounded = Math.round(scale * 4) / 4;
        return SCALE_LABELS[rounded] || 'Звичайний';
    }

    /* ── Карта значень → CSS-клас ───────────────────────── */
    const SCALE_CLASSES = {
        0.75: 'font-scale-075',
        1.25: 'font-scale-125',
        1.5:  'font-scale-150'
        // 1.0 — жодного класу: сайт виглядає як оригінал
    };
    const ALL_SCALE_CLASSES = Object.values(SCALE_CLASSES);

    /* ── Застосування налаштувань до DOM ────────────────── */
    function applyFontScale(scale) {
        const root = document.documentElement;
        // Спочатку знімаємо всі класи масштабу
        root.classList.remove(...ALL_SCALE_CLASSES);
        // Округлюємо щоб уникнути float-похибок (1.2500001 тощо)
        const rounded = Math.round(scale * 4) / 4;
        const cls = SCALE_CLASSES[rounded];
        // Для scale 1.0 cls = undefined → клас не додається
        // → font-size на html залишається браузерним дефолтом (16px)
        // → сайт виглядає абсолютно ідентично оригіналу
        if (cls) root.classList.add(cls);
    }

    function applyContrast(mode) {
        document.body.classList.toggle('high-contrast', mode === 'high');
    }

    function applyFont(mode) {
        document.body.classList.toggle('dyslexic-font', mode === 'dyslexic');
    }

    function applyAll(s) {
        applyFontScale(s.fontScale);
        applyContrast(s.contrast);
        applyFont(s.font);
    }

    /* ── Застосовуємо збережені налаштування одразу ─────── */
    const settings = load();
    applyAll(settings);

    /* ── Ініціалізація UI ───────────────────────────────── */
    document.addEventListener('DOMContentLoaded', function () {

        /* Елементи */
        const fab        = document.getElementById('a11y-fab');
        const fabIcon    = document.getElementById('a11y-fab-icon');
        const offEl      = document.getElementById('a11yOffcanvas');
        const offcanvas  = new bootstrap.Offcanvas(offEl);

        const slider     = document.getElementById('a11y-font-slider');
        const scaleBadge = document.getElementById('a11y-scale-badge');
        const btnMinus   = document.getElementById('a11y-font-minus');
        const btnPlus    = document.getElementById('a11y-font-plus');
        const btnRstFont = document.getElementById('a11y-reset-font');

        const btnCNormal = document.getElementById('a11y-contrast-normal');
        const btnCHigh   = document.getElementById('a11y-contrast-high');

        const btnFNormal   = document.getElementById('a11y-font-normal');
        const btnFDyslexic = document.getElementById('a11y-font-dyslexic');

        const btnRstAll  = document.getElementById('a11y-reset-all');

        /* ── Оновлення відображення масштабу ─────────────── */
        function showScale(scale) {
            slider.value = scale;
            scaleBadge.textContent = getScaleLabel(scale);
        }

        /* ── Синхронізація кнопок-варіантів ─────────────── */
        function syncBtn(activeBtn, ...btns) {
            btns.forEach(function (b) {
                b.classList.remove('active');
            });
            activeBtn.classList.add('active');
        }

        function syncUI(s) {
            showScale(s.fontScale);
            syncBtn(s.contrast === 'high' ? btnCHigh : btnCNormal, btnCNormal, btnCHigh);
            syncBtn(s.font === 'dyslexic'  ? btnFDyslexic : btnFNormal, btnFNormal, btnFDyslexic);
        }

        syncUI(settings);

        /* ── FAB: ♿ при нагорі, ↑ після прокрутки ────────── */
        function updateFab() {
            if (window.scrollY > 300) {
                fabIcon.className = 'bi bi-arrow-up-short';
                fab.setAttribute('title', 'Повернутись нагору');
                fab.setAttribute('aria-label', 'Повернутись нагору');
            } else {
                fabIcon.className = 'bi bi-universal-access';
                fab.setAttribute('title', 'Панель доступності');
                fab.setAttribute('aria-label', 'Панель доступності');
            }
        }
        updateFab();
        window.addEventListener('scroll', updateFab, { passive: true });

        fab.addEventListener('click', function () {
            if (window.scrollY > 300) {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            } else {
                offcanvas.show();
            }
        });

        /* ── Зміна масштабу ──────────────────────────────── */
        function setScale(raw) {
            // Прив'язуємо до допустимих значень: 0.75 / 1.0 / 1.25 / 1.5
            const scale = Math.min(1.5, Math.max(0.75, Math.round(raw / 0.25) * 0.25));
            settings.fontScale = scale;
            save(settings);
            applyFontScale(scale);
            showScale(scale);
        }

        slider.addEventListener('input', function () {
            setScale(parseFloat(this.value));
        });
        btnMinus.addEventListener('click', function () {
            setScale(settings.fontScale - 0.25);
        });
        btnPlus.addEventListener('click', function () {
            setScale(settings.fontScale + 0.25);
        });
        btnRstFont.addEventListener('click', function () {
            setScale(1.0);
        });

        /* ── Контрастність ───────────────────────────────── */
        btnCNormal.addEventListener('click', function () {
            settings.contrast = 'normal';
            save(settings);
            applyContrast('normal');
            syncBtn(btnCNormal, btnCNormal, btnCHigh);
        });
        btnCHigh.addEventListener('click', function () {
            settings.contrast = 'high';
            save(settings);
            applyContrast('high');
            syncBtn(btnCHigh, btnCNormal, btnCHigh);
        });

        /* ── Шрифт ───────────────────────────────────────── */
        btnFNormal.addEventListener('click', function () {
            settings.font = 'normal';
            save(settings);
            applyFont('normal');
            syncBtn(btnFNormal, btnFNormal, btnFDyslexic);
        });
        btnFDyslexic.addEventListener('click', function () {
            settings.font = 'dyslexic';
            save(settings);
            applyFont('dyslexic');
            syncBtn(btnFDyslexic, btnFNormal, btnFDyslexic);
        });

        /* ── Скинути все ─────────────────────────────────── */
        btnRstAll.addEventListener('click', function () {
            Object.assign(settings, DEFAULT);
            save(settings);
            applyAll(settings);
            syncUI(settings);
        });
    });

})();
