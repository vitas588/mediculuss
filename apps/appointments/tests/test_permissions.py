"""
Permission-тести для apps/appointments та apps/doctors.
Перевіряють що кожна роль має доступ тільки до дозволених ендпоінтів.

Матриця доступу:
  Ендпоінт                          Анонім  Пацієнт  Лікар  Адмін
  GET  /api/appointments/            401     200      200    200
  POST /api/appointments/            401     201      403    403
  PATCH /api/appointments/{id}/cancel/ 401  200*     403    403
  PATCH /api/appointments/{id}/complete/ 401 403     200*   403
  GET  /api/doctors/me/              401     403      200    403
  PUT  /api/doctors/me/photo/        401     403      200*   403

  * тільки власні ресурси

Запуск: python manage.py test apps.appointments.tests.test_permissions --verbosity=2
"""

from datetime import time, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Patient, User
from apps.appointments.models import Appointment
from apps.doctors.models import Doctor, DoctorSchedule, Specialty


# ---------------------------------------------------------------------------
# Допоміжні функції
# ---------------------------------------------------------------------------

def make_user(email, role=User.Role.PATIENT, verified=True):
    u = User.objects.create_user(
        email=email,
        first_name='Тест',
        last_name='Юзер',
        password='Test1234',
        role=role,
    )
    u.email_verified = verified
    u.save()
    return u


def auth(user):
    token = str(RefreshToken.for_user(user).access_token)
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


def future_dt(days=1, hour=10):
    return (timezone.now() + timedelta(days=days)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )


# ---------------------------------------------------------------------------
# Базовий setUp з усіма ролями
# ---------------------------------------------------------------------------

class BasePermissionTest(APITestCase):

    def setUp(self):
        specialty = Specialty.objects.create(name='Перм', slug='perm-test')

        # Лікар 1
        self.doctor_user = make_user('perm_doc@test.com', role=User.Role.DOCTOR)
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            specialty=specialty,
            is_active=True,
            slot_duration=30,
        )
        for day in range(7):
            DoctorSchedule.objects.create(
                doctor=self.doctor,
                day_of_week=day,
                work_start=time(8, 0),
                work_end=time(18, 0),
                is_working=True,
            )

        # Лікар 2 (чужий)
        specialty2 = Specialty.objects.create(name='Перм2', slug='perm-test-2')
        self.other_doctor_user = make_user('perm_doc2@test.com', role=User.Role.DOCTOR)
        self.other_doctor = Doctor.objects.create(
            user=self.other_doctor_user,
            specialty=specialty2,
            is_active=True,
            slot_duration=30,
        )

        # Пацієнт 1
        self.patient_user = make_user('perm_pat@test.com', role=User.Role.PATIENT)
        self.patient = Patient.objects.create(user=self.patient_user)

        # Пацієнт 2 (чужий)
        self.other_patient_user = make_user('perm_pat2@test.com', role=User.Role.PATIENT)
        self.other_patient = Patient.objects.create(user=self.other_patient_user)

        # Адміністратор
        self.admin_user = make_user('perm_admin@test.com', role=User.Role.ADMIN)

        # Записи
        self.apt = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date_time=future_dt(days=1),
            status='planned',
        )
        self.other_apt = Appointment.objects.create(
            patient=self.other_patient,
            doctor=self.doctor,
            date_time=future_dt(days=2),
            status='planned',
        )


# ---------------------------------------------------------------------------
# Анонімний користувач
# ---------------------------------------------------------------------------

class AnonymousPermissionTest(BasePermissionTest):
    """Анонімний не має доступу до жодного захищеного ендпоінту."""

    def test_cannot_list_appointments(self):
        resp = self.client.get('/api/appointments/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_create_appointment(self):
        resp = self.client.post('/api/appointments/', {
            'doctor_id': self.doctor.id,
            'date_time': future_dt().isoformat(),
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_cancel_appointment(self):
        resp = self.client.patch(f'/api/appointments/{self.apt.id}/cancel/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_complete_appointment(self):
        resp = self.client.patch(f'/api/appointments/{self.apt.id}/complete/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_access_doctor_profile(self):
        resp = self.client.get('/api/doctors/me/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_upload_doctor_photo(self):
        resp = self.client.put('/api/doctors/me/photo/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_view_medical_records(self):
        resp = self.client.get('/api/appointments/medical-records/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_access_own_schedule(self):
        resp = self.client.get('/api/doctors/me/schedule/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Пацієнт
# ---------------------------------------------------------------------------

class PatientPermissionTest(BasePermissionTest):
    """Пацієнт може: записуватись, скасовувати своє. Не може: завершувати, бачити чуже."""

    def test_can_list_own_appointments(self):
        resp = self.client.get('/api/appointments/', **auth(self.patient_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_can_create_appointment(self):
        resp = self.client.post(
            '/api/appointments/',
            {'doctor_id': self.doctor.id, 'date_time': future_dt(days=3, hour=9).isoformat()},
            format='json',
            **auth(self.patient_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_can_cancel_own_appointment(self):
        resp = self.client.patch(
            f'/api/appointments/{self.apt.id}/cancel/',
            **auth(self.patient_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_cannot_complete_appointment(self):
        resp = self.client.patch(
            f'/api/appointments/{self.apt.id}/complete/',
            {'diagnosis': 'Тест', 'treatment': 'Тест'},
            format='json',
            **auth(self.patient_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_cancel_other_patients_appointment(self):
        resp = self.client.patch(
            f'/api/appointments/{self.other_apt.id}/cancel/',
            **auth(self.patient_user),
        )
        # 404 — запис не знайдено для цього пацієнта
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_sees_only_own_appointments_in_list(self):
        resp = self.client.get('/api/appointments/', **auth(self.patient_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [a['id'] for a in resp.data['results']]
        self.assertIn(self.apt.id, ids)
        self.assertNotIn(self.other_apt.id, ids)

    def test_cannot_access_doctor_profile_endpoint(self):
        resp = self.client.get('/api/doctors/me/', **auth(self.patient_user))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_upload_doctor_photo(self):
        resp = self.client.put('/api/doctors/me/photo/', **auth(self.patient_user))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_access_doctor_schedule_endpoint(self):
        resp = self.client.get('/api/doctors/me/schedule/', **auth(self.patient_user))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Лікар
# ---------------------------------------------------------------------------

class DoctorPermissionTest(BasePermissionTest):
    """Лікар може: завершувати свій прийом, переглядати свій профіль/розклад.
    Не може: записуватись до лікарів, скасовувати записи пацієнтів."""

    def test_cannot_create_appointment(self):
        resp = self.client.post(
            '/api/appointments/',
            {'doctor_id': self.other_doctor.id, 'date_time': future_dt().isoformat()},
            format='json',
            **auth(self.doctor_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_cancel_patient_appointment(self):
        resp = self.client.patch(
            f'/api/appointments/{self.apt.id}/cancel/',
            **auth(self.doctor_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_can_complete_own_appointment(self):
        resp = self.client.patch(
            f'/api/appointments/{self.apt.id}/complete/',
            {'diagnosis': 'ГРВІ', 'treatment': 'Відпочинок'},
            format='json',
            **auth(self.doctor_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_cannot_complete_other_doctors_appointment(self):
        resp = self.client.patch(
            f'/api/appointments/{self.apt.id}/complete/',
            {'diagnosis': 'ГРВІ', 'treatment': 'Відпочинок'},
            format='json',
            **auth(self.other_doctor_user),
        )
        # 404 — запис не до цього лікаря
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_can_access_own_doctor_profile(self):
        resp = self.client.get('/api/doctors/me/', **auth(self.doctor_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['full_name'], self.doctor_user.get_full_name())

    def test_can_access_own_schedule(self):
        resp = self.client.get('/api/doctors/me/schedule/', **auth(self.doctor_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_sees_only_own_appointments_in_list(self):
        resp = self.client.get('/api/appointments/', **auth(self.doctor_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Лікар бачить лише записи до нього
        for apt in resp.data['results']:
            self.assertEqual(apt['doctor_id'], self.doctor.id)

    def test_cannot_view_medical_records_as_doctor(self):
        # /medical-records/ тільки для пацієнтів
        resp = self.client.get('/api/appointments/medical-records/', **auth(self.doctor_user))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Ізоляція даних між пацієнтами
# ---------------------------------------------------------------------------

class DataIsolationTest(BasePermissionTest):
    """Пацієнт не може отримати дані іншого пацієнта."""

    def test_patient_cannot_view_other_appointment_detail(self):
        resp = self.client.get(
            f'/api/appointments/{self.other_apt.id}/',
            **auth(self.patient_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_patients_appointments_are_isolated_in_list(self):
        resp1 = self.client.get('/api/appointments/', **auth(self.patient_user))
        resp2 = self.client.get('/api/appointments/', **auth(self.other_patient_user))

        ids1 = {a['id'] for a in resp1.data['results']}
        ids2 = {a['id'] for a in resp2.data['results']}

        self.assertEqual(ids1 & ids2, set())  # перетин порожній

    def test_patient_cannot_cancel_appointment_belonging_to_other(self):
        resp = self.client.patch(
            f'/api/appointments/{self.other_apt.id}/cancel/',
            **auth(self.patient_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        # Запис не змінився
        self.other_apt.refresh_from_db()
        self.assertEqual(self.other_apt.status, 'planned')
