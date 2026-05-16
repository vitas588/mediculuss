"""
Інтеграційні тести для apps/appointments.
Перевіряють повний цикл від HTTP-запиту до стану бази даних.

Запуск: python manage.py test apps.appointments.tests.test_integration --verbosity=2
"""

from datetime import time, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Patient, User
from apps.appointments.models import Appointment, MedicalRecord
from apps.doctors.models import Doctor, DoctorSchedule, Specialty
from apps.notifications.models import Notification


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
# Реєстрація та верифікація email
# ---------------------------------------------------------------------------

class RegistrationFlowTest(APITestCase):
    """Повний цикл: реєстрація → верифікація → JWT токени."""

    REGISTER_DATA = {
        'email': 'flow@test.com',
        'first_name': 'Потік',
        'last_name': 'Тест',
        'password': 'Test1234',
        'password_confirm': 'Test1234',
    }

    def test_registration_returns_201_and_requires_verification(self):
        resp = self.client.post('/api/auth/register/', self.REGISTER_DATA, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data['requires_verification'])
        self.assertEqual(resp.data['email'], 'flow@test.com')

    def test_registration_creates_user_with_unverified_email(self):
        self.client.post('/api/auth/register/', self.REGISTER_DATA, format='json')
        user = User.objects.get(email='flow@test.com')
        self.assertFalse(user.email_verified)
        self.assertIsNotNone(user.email_verification_code)
        self.assertIsNotNone(user.email_verification_code_expires)

    def test_registration_creates_patient_profile(self):
        self.client.post('/api/auth/register/', self.REGISTER_DATA, format='json')
        self.assertTrue(Patient.objects.filter(user__email='flow@test.com').exists())

    def test_verification_with_correct_code_returns_tokens(self):
        self.client.post('/api/auth/register/', self.REGISTER_DATA, format='json')
        user = User.objects.get(email='flow@test.com')
        code = user.email_verification_code

        resp = self.client.post('/api/auth/verify-email/', {
            'email': 'flow@test.com',
            'code': code,
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', resp.data)
        self.assertIn('access', resp.data['tokens'])
        self.assertIn('refresh', resp.data['tokens'])

        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertIsNone(user.email_verification_code)

    def test_verification_with_wrong_code_fails(self):
        self.client.post('/api/auth/register/', self.REGISTER_DATA, format='json')
        resp = self.client.post('/api/auth/verify-email/', {
            'email': 'flow@test.com',
            'code': '000000',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verification_with_expired_code_fails(self):
        self.client.post('/api/auth/register/', self.REGISTER_DATA, format='json')
        user = User.objects.get(email='flow@test.com')
        code = user.email_verification_code
        user.email_verification_code_expires = timezone.now() - timedelta(minutes=1)
        user.save()

        resp = self.client.post('/api/auth/verify-email/', {
            'email': 'flow@test.com',
            'code': code,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Авторизація
# ---------------------------------------------------------------------------

class LoginFlowTest(APITestCase):
    """Тести входу в систему."""

    def setUp(self):
        self.user = make_user('login_int@test.com', verified=True)

    def test_login_verified_user_returns_tokens(self):
        resp = self.client.post('/api/auth/login/', {
            'email': 'login_int@test.com',
            'password': 'Test1234',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data['tokens'])
        self.assertIn('refresh', resp.data['tokens'])
        self.assertEqual(resp.data['user']['role'], 'patient')

    def test_login_unverified_user_returns_403(self):
        self.user.email_verified = False
        self.user.save()
        resp = self.client.post('/api/auth/login/', {
            'email': 'login_int@test.com',
            'password': 'Test1234',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(resp.data['error'], 'email_not_verified')

    def test_login_wrong_password_returns_400(self):
        resp = self.client.post('/api/auth/login/', {
            'email': 'login_int@test.com',
            'password': 'WrongPass9',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Запис до лікаря
# ---------------------------------------------------------------------------

class AppointmentBookingFlowTest(APITestCase):
    """Повний цикл: перегляд слотів → запис → скасування."""

    def setUp(self):
        specialty = Specialty.objects.create(name='Терапія', slug='terapiia-int')

        self.doctor_user = make_user('doc_int@test.com', role=User.Role.DOCTOR)
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

        self.patient_user = make_user('pat_int@test.com', role=User.Role.PATIENT)
        self.patient = Patient.objects.create(user=self.patient_user)

        self.apt_time = future_dt(days=1, hour=10)

    def test_available_slots_returned_for_working_day(self):
        tomorrow = (timezone.now() + timedelta(days=1)).date()
        resp = self.client.get(
            f'/api/doctors/{self.doctor.id}/available-slots/',
            {'date': tomorrow.isoformat()},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(len(resp.data['slots']), 0)

    def test_create_appointment_returns_201(self):
        resp = self.client.post(
            '/api/appointments/',
            {'doctor_id': self.doctor.id, 'date_time': self.apt_time.isoformat(), 'reason': 'Болить'},
            format='json',
            **auth(self.patient_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['status'], 'planned')

    def test_create_appointment_saves_to_db(self):
        self.client.post(
            '/api/appointments/',
            {'doctor_id': self.doctor.id, 'date_time': self.apt_time.isoformat()},
            format='json',
            **auth(self.patient_user),
        )
        self.assertTrue(
            Appointment.objects.filter(patient=self.patient, doctor=self.doctor).exists()
        )

    def test_create_appointment_sends_notification_to_patient(self):
        before = Notification.objects.filter(user=self.patient_user).count()
        self.client.post(
            '/api/appointments/',
            {'doctor_id': self.doctor.id, 'date_time': self.apt_time.isoformat()},
            format='json',
            **auth(self.patient_user),
        )
        after = Notification.objects.filter(user=self.patient_user).count()
        self.assertEqual(after, before + 1)

    def test_double_booking_same_slot_rejected(self):
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date_time=self.apt_time,
            status='planned',
        )
        other_user = make_user('other_int@test.com', role=User.Role.PATIENT)
        Patient.objects.create(user=other_user)

        resp = self.client.post(
            '/api/appointments/',
            {'doctor_id': self.doctor.id, 'date_time': self.apt_time.isoformat()},
            format='json',
            **auth(other_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelled_slot_is_freed(self):
        apt = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date_time=self.apt_time,
            status='cancelled',
        )
        other_user = make_user('freed_int@test.com', role=User.Role.PATIENT)
        Patient.objects.create(user=other_user)

        resp = self.client.post(
            '/api/appointments/',
            {'doctor_id': self.doctor.id, 'date_time': self.apt_time.isoformat()},
            format='json',
            **auth(other_user),
        )
        self.assertNotEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_appointment_changes_status(self):
        apt = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date_time=self.apt_time,
            status='planned',
        )
        resp = self.client.patch(
            f'/api/appointments/{apt.id}/cancel/',
            format='json',
            **auth(self.patient_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        apt.refresh_from_db()
        self.assertEqual(apt.status, 'cancelled')

    def test_cancel_appointment_notifies_doctor(self):
        apt = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date_time=self.apt_time,
            status='planned',
        )
        before = Notification.objects.filter(user=self.doctor_user).count()
        self.client.patch(
            f'/api/appointments/{apt.id}/cancel/',
            format='json',
            **auth(self.patient_user),
        )
        after = Notification.objects.filter(user=self.doctor_user).count()
        self.assertEqual(after, before + 1)


# ---------------------------------------------------------------------------
# Завершення прийому та медична картка
# ---------------------------------------------------------------------------

class CompleteAppointmentFlowTest(APITestCase):
    """Завершення прийому лікарем — збереження медичної картки."""

    def setUp(self):
        specialty = Specialty.objects.create(name='Хірургія', slug='khirurhiia-int')

        self.doctor_user = make_user('doc_complete@test.com', role=User.Role.DOCTOR)
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            specialty=specialty,
            is_active=True,
            slot_duration=30,
        )
        self.patient_user = make_user('pat_complete@test.com', role=User.Role.PATIENT)
        self.patient = Patient.objects.create(user=self.patient_user)

        self.apt = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date_time=timezone.now() - timedelta(hours=1),
            status='planned',
        )

    def test_complete_changes_status_to_completed(self):
        resp = self.client.patch(
            f'/api/appointments/{self.apt.id}/complete/',
            {'diagnosis': 'ГРВІ', 'treatment': 'Відпочинок'},
            format='json',
            **auth(self.doctor_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.apt.refresh_from_db()
        self.assertEqual(self.apt.status, 'completed')

    def test_complete_creates_medical_record(self):
        self.client.patch(
            f'/api/appointments/{self.apt.id}/complete/',
            {
                'diagnosis': 'ГРВІ легкого ступеня',
                'treatment': 'Парацетамол 500мг',
                'doctor_notes': 'Приватна нотатка',
            },
            format='json',
            **auth(self.doctor_user),
        )
        self.assertTrue(MedicalRecord.objects.filter(appointment=self.apt).exists())
        record = MedicalRecord.objects.get(appointment=self.apt)
        self.assertEqual(record.diagnosis, 'ГРВІ легкого ступеня')
        self.assertEqual(record.treatment, 'Парацетамол 500мг')

    def test_complete_notifies_patient(self):
        before = Notification.objects.filter(user=self.patient_user).count()
        self.client.patch(
            f'/api/appointments/{self.apt.id}/complete/',
            {'diagnosis': 'Тест', 'treatment': 'Тест'},
            format='json',
            **auth(self.doctor_user),
        )
        after = Notification.objects.filter(user=self.patient_user).count()
        self.assertEqual(after, before + 1)

    def test_complete_without_diagnosis_fails(self):
        resp = self.client.patch(
            f'/api/appointments/{self.apt.id}/complete/',
            {'treatment': 'Тест'},
            format='json',
            **auth(self.doctor_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_already_completed_appointment_cannot_be_completed_again(self):
        self.apt.status = 'completed'
        self.apt.save()
        resp = self.client.patch(
            f'/api/appointments/{self.apt.id}/complete/',
            {'diagnosis': 'Тест', 'treatment': 'Тест'},
            format='json',
            **auth(self.doctor_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Перегляд медичних записів пацієнтом
# ---------------------------------------------------------------------------

class MedicalRecordViewTest(APITestCase):
    """Пацієнт бачить діагноз; лікар бачить і нотатки."""

    def setUp(self):
        specialty = Specialty.objects.create(name='Невро', slug='nevro-int')

        self.doctor_user = make_user('doc_med@test.com', role=User.Role.DOCTOR)
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            specialty=specialty,
            is_active=True,
            slot_duration=30,
        )
        self.patient_user = make_user('pat_med@test.com', role=User.Role.PATIENT)
        self.patient = Patient.objects.create(user=self.patient_user)

        self.apt = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date_time=timezone.now() - timedelta(hours=2),
            status='completed',
        )
        MedicalRecord.objects.create(
            appointment=self.apt,
            diagnosis='Мігрень',
            treatment='Ібупрофен 400мг',
            doctor_notes='Підозра на хронічне',
        )

    def test_patient_can_view_appointment_with_medical_record(self):
        resp = self.client.get(
            f'/api/appointments/{self.apt.id}/',
            **auth(self.patient_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('medical_record', resp.data)
        self.assertEqual(resp.data['medical_record']['diagnosis'], 'Мігрень')

    def test_medical_records_list_returns_only_completed(self):
        resp = self.client.get(
            '/api/appointments/medical-records/',
            **auth(self.patient_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(resp.data['count'], 0)
