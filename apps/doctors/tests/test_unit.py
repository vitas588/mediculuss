"""
Unit/Integration-тести алгоритму генерації вільних часових проміжків.
Перевіряють логіку DoctorAvailableSlotsView ізольовано для кожного сценарію.

Запуск: python manage.py test apps.doctors.tests.test_unit --verbosity=2
"""

from datetime import datetime, time, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Patient, User
from apps.appointments.models import Appointment
from apps.doctors.models import Doctor, DoctorSchedule, Specialty


# ---------------------------------------------------------------------------
# Допоміжні функції
# ---------------------------------------------------------------------------

def make_doctor(email='slot_doc@test.com', slot_duration=30):
    specialty, _ = Specialty.objects.get_or_create(
        slug='slot-test', defaults={'name': 'Слот-тест'}
    )
    user = User.objects.create_user(
        email=email,
        first_name='Слот',
        last_name='Лікар',
        password='Test1234',
        role=User.Role.DOCTOR,
    )
    return Doctor.objects.create(
        user=user,
        specialty=specialty,
        is_active=True,
        slot_duration=slot_duration,
    )


def make_patient(email='slot_pat@test.com'):
    user = User.objects.create_user(
        email=email,
        first_name='П',
        last_name='А',
        password='Test1234',
        role=User.Role.PATIENT,
    )
    return Patient.objects.create(user=user)


def add_schedule(doctor, day_of_week, start=time(8, 0), end=time(10, 0)):
    return DoctorSchedule.objects.create(
        doctor=doctor,
        day_of_week=day_of_week,
        work_start=start,
        work_end=end,
        is_working=True,
    )


def next_date_for_dow(dow, min_days=1):
    """Повертає найближчу майбутню дату з потрібним днем тижня."""
    today = timezone.now().date()
    for i in range(min_days, min_days + 7):
        candidate = today + timedelta(days=i)
        if candidate.weekday() == dow:
            return candidate
    return None


# ---------------------------------------------------------------------------
# Генерація слотів — кількість і час
# ---------------------------------------------------------------------------

class SlotCountTest(APITestCase):
    """Перевірка що кількість слотів відповідає розкладу."""

    def setUp(self):
        self.doctor = make_doctor('sc_doc@test.com', slot_duration=30)
        # Понеділок (0): 9:00–11:00 = 4 слоти по 30 хв
        add_schedule(self.doctor, day_of_week=0, start=time(9, 0), end=time(11, 0))
        self.monday = next_date_for_dow(0)

    def _slots(self, date):
        resp = self.client.get(
            f'/api/doctors/{self.doctor.id}/available-slots/',
            {'date': date.isoformat()},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return resp.data['slots']

    def test_four_slots_for_two_hour_schedule(self):
        """9:00–11:00 / 30 хв = 4 слоти."""
        slots = self._slots(self.monday)
        self.assertEqual(len(slots), 4)

    def test_slot_times_match_schedule(self):
        """Перший слот 09:00, останній 10:30."""
        slots = self._slots(self.monday)
        times = [s['time'] for s in slots]
        self.assertIn('09:00', times)
        self.assertIn('10:30', times)
        self.assertNotIn('11:00', times)

    def test_slot_duration_60_gives_2_slots(self):
        """60-хвилинний прийом: 9:00–11:00 = 2 слоти."""
        doctor2 = make_doctor('sc_doc2@test.com', slot_duration=60)
        add_schedule(doctor2, day_of_week=0, start=time(9, 0), end=time(11, 0))
        slots = self._slots(self.monday)
        # self.doctor has 30-min slots; doctor2 has 60-min
        resp2 = self.client.get(
            f'/api/doctors/{doctor2.id}/available-slots/',
            {'date': self.monday.isoformat()},
        )
        self.assertEqual(len(resp2.data['slots']), 2)

    def test_response_contains_doctor_name_and_slot_duration(self):
        resp = self.client.get(
            f'/api/doctors/{self.doctor.id}/available-slots/',
            {'date': self.monday.isoformat()},
        )
        self.assertIn('doctor', resp.data)
        self.assertIn('slot_duration', resp.data)
        self.assertEqual(resp.data['slot_duration'], 30)


# ---------------------------------------------------------------------------
# Фільтрація зайнятих слотів
# ---------------------------------------------------------------------------

class BookedSlotFilterTest(APITestCase):
    """Зайняті слоти виключаються зі списку доступних."""

    def setUp(self):
        self.doctor = make_doctor('bsf_doc@test.com', slot_duration=30)
        self.patient = make_patient('bsf_pat@test.com')
        add_schedule(self.doctor, day_of_week=1, start=time(9, 0), end=time(11, 0))  # вівторок
        self.tuesday = next_date_for_dow(1)

    def _get_times(self):
        resp = self.client.get(
            f'/api/doctors/{self.doctor.id}/available-slots/',
            {'date': self.tuesday.isoformat()},
        )
        return [s['time'] for s in resp.data.get('slots', [])]

    def _make_apt(self, hour, status='planned'):
        dt = timezone.make_aware(
            datetime(self.tuesday.year, self.tuesday.month, self.tuesday.day, hour, 0)
        )
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date_time=dt,
            status=status,
        )

    def test_planned_appointment_removes_slot(self):
        self._make_apt(9, status='planned')
        times = self._get_times()
        self.assertNotIn('09:00', times)
        self.assertIn('09:30', times)

    def test_completed_appointment_removes_slot(self):
        self._make_apt(9, status='completed')
        times = self._get_times()
        self.assertNotIn('09:00', times)

    def test_cancelled_appointment_does_not_block_slot(self):
        self._make_apt(9, status='cancelled')
        times = self._get_times()
        self.assertIn('09:00', times)

    def test_missed_appointment_does_not_block_slot(self):
        self._make_apt(9, status='missed')
        times = self._get_times()
        self.assertIn('09:00', times)

    def test_all_slots_booked_returns_empty_list(self):
        for hour in [9, 9, 10]:  # 9:00, 9:30, 10:00, 10:30 → 4 слоти
            pass
        for minute_offset in [0, 30]:
            dt = timezone.make_aware(
                datetime(self.tuesday.year, self.tuesday.month, self.tuesday.day, 9, minute_offset)
            )
            Appointment.objects.create(
                patient=self.patient,
                doctor=self.doctor,
                date_time=dt,
                status='planned',
            )
            dt2 = timezone.make_aware(
                datetime(self.tuesday.year, self.tuesday.month, self.tuesday.day, 10, minute_offset)
            )
            Appointment.objects.create(
                patient=self.patient,
                doctor=self.doctor,
                date_time=dt2,
                status='planned',
            )
        times = self._get_times()
        self.assertEqual(len(times), 0)


# ---------------------------------------------------------------------------
# Робочі / вихідні дні
# ---------------------------------------------------------------------------

class WorkingDayTest(APITestCase):
    """Перевірка розрізнення робочих і вихідних днів."""

    def setUp(self):
        self.doctor = make_doctor('wd_doc@test.com')
        # Тільки середа (2) — робочий день
        add_schedule(self.doctor, day_of_week=2, start=time(9, 0), end=time(11, 0))

    def test_working_day_returns_slots(self):
        wednesday = next_date_for_dow(2)
        resp = self.client.get(
            f'/api/doctors/{self.doctor.id}/available-slots/',
            {'date': wednesday.isoformat()},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(len(resp.data['slots']), 0)

    def test_non_working_day_returns_empty_slots(self):
        # Четвер (3) — не робочий
        thursday = next_date_for_dow(3)
        resp = self.client.get(
            f'/api/doctors/{self.doctor.id}/available-slots/',
            {'date': thursday.isoformat()},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data.get('slots', []), [])

    def test_non_working_day_returns_message(self):
        thursday = next_date_for_dow(3)
        resp = self.client.get(
            f'/api/doctors/{self.doctor.id}/available-slots/',
            {'date': thursday.isoformat()},
        )
        self.assertIn('message', resp.data)


# ---------------------------------------------------------------------------
# Валідація вхідних даних
# ---------------------------------------------------------------------------

class SlotInputValidationTest(APITestCase):
    """Перевірка серверної валідації параметра date."""

    def setUp(self):
        self.doctor = make_doctor('siv_doc@test.com')
        add_schedule(self.doctor, day_of_week=0, start=time(9, 0), end=time(11, 0))

    def _get(self, date_str):
        return self.client.get(
            f'/api/doctors/{self.doctor.id}/available-slots/',
            {'date': date_str},
        )

    def test_missing_date_returns_400(self):
        resp = self.client.get(f'/api/doctors/{self.doctor.id}/available-slots/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_date_format_returns_400(self):
        resp = self._get('14-05-2026')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_past_date_returns_400(self):
        past = (timezone.now().date() - timedelta(days=1)).isoformat()
        resp = self._get(past)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_date_more_than_14_days_returns_400(self):
        far = (timezone.now().date() + timedelta(days=15)).isoformat()
        resp = self._get(far)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_date_exactly_14_days_returns_200(self):
        boundary = (timezone.now().date() + timedelta(days=14)).isoformat()
        resp = self._get(boundary)
        self.assertIn(resp.status_code, [status.HTTP_200_OK])

    def test_inactive_doctor_returns_404(self):
        self.doctor.is_active = False
        self.doctor.save()
        monday = next_date_for_dow(0).isoformat()
        resp = self._get(monday)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_doctor_returns_404(self):
        resp = self.client.get(
            '/api/doctors/99999/available-slots/',
            {'date': timezone.now().date().isoformat()},
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
