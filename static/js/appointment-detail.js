/**
 * ============================================
 * Mediculus Hospital - Деталі запису
 * ============================================
 * APPOINTMENT_ID передається з Django template.
 */

document.addEventListener('DOMContentLoaded', async () => {
    if (!isAuthenticated()) {
        window.location.href = '/login/';
        return;
    }
    await loadAppointmentDetail();
});

async function loadAppointmentDetail() {
    const loader = document.getElementById('detail-loader');
    const content = document.getElementById('detail-content');
    const currentUser = getCurrentUser();
    const isDoctor = currentUser && currentUser.role === 'doctor';

    // Адаптуємо breadcrumbs та заголовки для лікаря
    if (isDoctor) {
        const breadcrumbLink = document.getElementById('breadcrumb-appointments-link');
        if (breadcrumbLink) {
            breadcrumbLink.href = '/appointments/doctor/';
            breadcrumbLink.textContent = 'Мої пацієнти';
        }
    }

    try {
        const response = await apiRequest(`/appointments/${APPOINTMENT_ID}/`);
        if (!response || !response.ok) {
            loader.innerHTML = '<div class="alert alert-danger">Запис не знайдено.</div>';
            return;
        }

        const apt = await response.json();

        // Заповнюємо дані
        const dateTime = new Date(apt.date_time);
        const dateFormatted = dateTime.toLocaleDateString('uk-UA', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        });
        const timeFormatted = dateTime.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });

        document.getElementById('detail-doctor').textContent = apt.doctor_name;
        document.getElementById('detail-specialty').textContent = apt.doctor_specialty;
        document.getElementById('detail-datetime').textContent = `${dateFormatted} о ${timeFormatted}`;
        document.getElementById('detail-created').textContent = new Date(apt.created_at).toLocaleDateString('uk-UA');

        if (apt.reason) {
            document.getElementById('detail-reason').textContent = apt.reason;
        } else {
            document.getElementById('detail-reason-row')?.classList.add('d-none');
        }

        // Статус
        const statusColors = { planned: 'primary', completed: 'success', cancelled: 'danger', missed: 'warning' };
        const statusBadge = document.getElementById('detail-status-badge');
        if (statusBadge) {
            statusBadge.textContent = apt.status_display;
            statusBadge.className = `badge fs-6 bg-${statusColors[apt.status] || 'secondary'}`;
        }

        // Права панель: залежно від ролі показуємо лікаря або пацієнта
        if (isDoctor) {
            // Лікар бачить інформацію про пацієнта
            document.getElementById('detail-side-title').innerHTML =
                '<i class="bi bi-person me-2 text-primary"></i>Пацієнт';
            document.getElementById('detail-doctor-panel').classList.add('d-none');
            document.getElementById('detail-patient-panel').classList.remove('d-none');
            document.getElementById('detail-patient-name').textContent = apt.patient_name;
            document.getElementById('detail-patient-phone').textContent = apt.patient_phone || '—';
        } else {
            // Пацієнт бачить інформацію про лікаря
            if (apt.doctor_photo) {
                document.getElementById('detail-doctor-photo').src = apt.doctor_photo;
            }
            document.getElementById('detail-doctor-name').textContent = apt.doctor_name;
            document.getElementById('detail-doctor-specialty').textContent = apt.doctor_specialty;
            if (apt.doctor_id) {
                document.getElementById('detail-doctor-link').href = `/doctors/${apt.doctor_id}/`;
            }
        }

        // Кнопка скасування — приховуємо для лікаря
        const cancelRow = document.getElementById('cancel-btn-row');
        if (cancelRow) {
            if (isDoctor || !apt.is_cancellable) {
                cancelRow.classList.add('d-none');
            } else {
                document.getElementById('cancel-appointment-btn')?.addEventListener('click', () => cancelAppointment(apt.id));
            }
        }

        // Медична картка
        if (apt.medical_record) {
            const mrCard = document.getElementById('medical-record-card');
            if (mrCard) {
                mrCard.classList.remove('d-none');
                document.getElementById('mr-diagnosis').textContent = apt.medical_record.diagnosis;
                document.getElementById('mr-treatment').textContent = apt.medical_record.treatment;
                document.getElementById('mr-created').textContent = new Date(apt.medical_record.created_at).toLocaleDateString('uk-UA');

                // Для лікаря — підпис медичної картки з ім'ям пацієнта
                if (isDoctor) {
                    const mrTitle = document.getElementById('medical-card-title');
                    if (mrTitle) {
                        mrTitle.innerHTML = `<i class="bi bi-file-medical me-2"></i>Результати прийому — ${escapeHtml(apt.patient_name)}`;
                    }
                }
            }
        }

        loader.classList.add('d-none');
        content.classList.remove('d-none');

    } catch (e) {
        console.error(e);
        loader.innerHTML = '<div class="alert alert-danger">Помилка завантаження.</div>';
    }
}

async function cancelAppointment(id) {
    if (!confirm('Ви впевнені що хочете скасувати цей запис?')) return;

    const btn = document.getElementById('cancel-appointment-btn');
    const errorDiv = document.getElementById('cancel-error');
    if (btn) btn.disabled = true;

    try {
        const response = await apiRequest(`/appointments/${id}/cancel/`, { method: 'PATCH' });
        if (response && response.ok) {
            window.location.reload();
        } else {
            const data = await response?.json();
            if (errorDiv) {
                errorDiv.textContent = data?.error || 'Помилка скасування.';
                errorDiv.classList.remove('d-none');
            }
            if (btn) btn.disabled = false;
        }
    } catch (e) {
        if (errorDiv) {
            errorDiv.textContent = 'Помилка з\'єднання.';
            errorDiv.classList.remove('d-none');
        }
        if (btn) btn.disabled = false;
    }
}
