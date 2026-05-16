"""
Unit-тести для apps/accounts.
Перевіряють методи моделей та валідацію серіалізаторів ізольовано від API.

Запуск: python manage.py test apps.accounts.tests.test_unit --verbosity=2
"""

from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Patient, User
from apps.accounts.serializers import RegisterSerializer


# ---------------------------------------------------------------------------
# Допоміжна функція
# ---------------------------------------------------------------------------

def make_user(email='u@test.com', role=User.Role.PATIENT, **kwargs):
    return User.objects.create_user(
        email=email,
        first_name='Тест',
        last_name='Юзер',
        password='Test1234',
        role=role,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Модель User
# ---------------------------------------------------------------------------

class UserModelTest(TestCase):

    def setUp(self):
        self.user = make_user(
            email='model@test.com',
            role=User.Role.PATIENT,
        )
        self.user.patronymic = 'Васильович'
        self.user.last_name = 'Петренко'
        self.user.first_name = 'Іван'
        self.user.save()

    def test_get_full_name_with_patronymic(self):
        self.assertEqual(self.user.get_full_name(), 'Петренко Іван Васильович')

    def test_get_full_name_without_patronymic(self):
        self.user.patronymic = ''
        self.assertEqual(self.user.get_full_name(), 'Петренко Іван')

    def test_is_patient_true_for_patient_role(self):
        self.assertTrue(self.user.is_patient)
        self.assertFalse(self.user.is_doctor)
        self.assertFalse(self.user.is_admin_user)

    def test_is_doctor_true_for_doctor_role(self):
        self.user.role = User.Role.DOCTOR
        self.assertTrue(self.user.is_doctor)
        self.assertFalse(self.user.is_patient)

    def test_is_admin_true_for_admin_role(self):
        self.user.role = User.Role.ADMIN
        self.assertTrue(self.user.is_admin_user)

    def test_password_is_hashed(self):
        self.assertNotEqual(self.user.password, 'Test1234')
        self.assertTrue(self.user.check_password('Test1234'))

    def test_default_role_is_patient(self):
        user = User.objects.create_user(
            email='def@test.com',
            first_name='А',
            last_name='Б',
            password='Test1234',
        )
        self.assertEqual(user.role, User.Role.PATIENT)

    def test_str_contains_email(self):
        self.assertIn('model@test.com', str(self.user))

    def test_email_verified_default_false(self):
        user = make_user(email='fresh@test.com')
        self.assertFalse(user.email_verified)

    def test_is_deleted_default_false(self):
        user = make_user(email='notdel@test.com')
        self.assertFalse(user.is_deleted)


# ---------------------------------------------------------------------------
# Модель Patient
# ---------------------------------------------------------------------------

class PatientModelTest(TestCase):

    def setUp(self):
        self.user = make_user(email='patient_model@test.com')
        self.patient = Patient.objects.create(
            user=self.user,
            date_of_birth=date(1990, 6, 15),
        )

    def test_get_age_correct(self):
        today = timezone.now().date()
        expected = today.year - 1990 - (
            (today.month, today.day) < (6, 15)
        )
        self.assertEqual(self.patient.get_age(), expected)

    def test_get_age_returns_none_without_dob(self):
        self.patient.date_of_birth = None
        self.assertIsNone(self.patient.get_age())

    def test_patient_linked_to_user(self):
        self.assertEqual(self.patient.user, self.user)

    def test_str_contains_full_name(self):
        self.assertIn('Юзер', str(self.patient))


# ---------------------------------------------------------------------------
# RegisterSerializer — валідація
# ---------------------------------------------------------------------------

class RegisterSerializerValidationTest(TestCase):

    BASE = {
        'email': 'new@test.com',
        'first_name': 'Тест',
        'last_name': 'Юзер',
        'password': 'Test1234',
        'password_confirm': 'Test1234',
    }

    def _s(self, data):
        return RegisterSerializer(data=data)

    # --- Позитивні ---

    def test_valid_data_is_valid(self):
        s = self._s(self.BASE)
        self.assertTrue(s.is_valid(), s.errors)

    def test_email_normalized_to_lowercase(self):
        s = self._s({**self.BASE, 'email': 'UPPER@TEST.COM'})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data['email'], 'upper@test.com')

    def test_optional_fields_not_required(self):
        data = {k: v for k, v in self.BASE.items()
                if k not in ('patronymic', 'phone', 'date_of_birth', 'gender')}
        s = self._s(data)
        self.assertTrue(s.is_valid(), s.errors)

    def test_create_builds_user_and_patient(self):
        s = self._s(self.BASE)
        self.assertTrue(s.is_valid())
        user = s.save()
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.role, User.Role.PATIENT)
        self.assertTrue(Patient.objects.filter(user=user).exists())

    # --- Негативні ---

    def test_duplicate_email_fails(self):
        make_user(email='new@test.com')
        s = self._s(self.BASE)
        self.assertFalse(s.is_valid())
        self.assertIn('email', s.errors)

    def test_password_mismatch_fails(self):
        s = self._s({**self.BASE, 'password_confirm': 'Different9'})
        self.assertFalse(s.is_valid())
        self.assertIn('password_confirm', s.errors)

    def test_password_without_digit_fails(self):
        s = self._s({**self.BASE,
                     'password': 'OnlyLetters',
                     'password_confirm': 'OnlyLetters'})
        self.assertFalse(s.is_valid())

    def test_password_without_letter_fails(self):
        s = self._s({**self.BASE,
                     'password': '12345678',
                     'password_confirm': '12345678'})
        self.assertFalse(s.is_valid())

    def test_short_password_fails(self):
        s = self._s({**self.BASE,
                     'password': 'Te1',
                     'password_confirm': 'Te1'})
        self.assertFalse(s.is_valid())

    def test_missing_first_name_fails(self):
        data = {k: v for k, v in self.BASE.items() if k != 'first_name'}
        s = self._s(data)
        self.assertFalse(s.is_valid())
        self.assertIn('first_name', s.errors)

    def test_missing_last_name_fails(self):
        data = {k: v for k, v in self.BASE.items() if k != 'last_name'}
        s = self._s(data)
        self.assertFalse(s.is_valid())
        self.assertIn('last_name', s.errors)


# ---------------------------------------------------------------------------
# AppointmentCreateSerializer — валідація дати
# ---------------------------------------------------------------------------

class AppointmentDateValidationTest(TestCase):

    def setUp(self):
        from apps.doctors.models import Doctor, Specialty
        from rest_framework.test import APIRequestFactory

        specialty = Specialty.objects.create(name='Тест', slug='test-unit')
        self.doctor_user = make_user('doc_unit@test.com', role=User.Role.DOCTOR)
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            specialty=specialty,
            is_active=True,
            slot_duration=30,
        )
        self.patient_user = make_user('pat_unit@test.com', role=User.Role.PATIENT)

        factory = APIRequestFactory()
        self.request = factory.post('/')
        self.request.user = self.patient_user

    def _s(self, date_time):
        from apps.appointments.serializers import AppointmentCreateSerializer
        return AppointmentCreateSerializer(
            data={'doctor_id': self.doctor.id, 'date_time': date_time},
            context={'request': self.request},
        )

    def test_past_datetime_rejected(self):
        past = (timezone.now() - timedelta(hours=1)).isoformat()
        s = self._s(past)
        self.assertFalse(s.is_valid())
        self.assertIn('date_time', s.errors)

    def test_more_than_14_days_rejected(self):
        far = (timezone.now() + timedelta(days=20)).isoformat()
        s = self._s(far)
        self.assertFalse(s.is_valid())
        self.assertIn('date_time', s.errors)
