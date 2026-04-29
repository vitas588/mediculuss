from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email обов\'язковий')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    class Role(models.TextChoices):
        PATIENT = 'patient', 'Пацієнт'
        DOCTOR = 'doctor', 'Лікар'
        ADMIN = 'admin', 'Адміністратор'

    email = models.EmailField(
        unique=True,
        verbose_name='Email'
    )
    first_name = models.CharField(
        max_length=100,
        verbose_name='Ім\'я'
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name='Прізвище'
    )
    patronymic = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='По-батькові'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Телефон'
    )

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PATIENT,
        verbose_name='Роль'
    )

    is_active = models.BooleanField(default=True, verbose_name='Активний')
    is_staff = models.BooleanField(default=False, verbose_name='Персонал')

    created_at = models.DateTimeField(default=timezone.now, verbose_name='Дата реєстрації')

    email_verified = models.BooleanField(default=False, verbose_name='Email підтверджено')
    email_verification_code = models.CharField(max_length=6, null=True, blank=True, verbose_name='Код верифікації email')
    email_verification_code_expires = models.DateTimeField(null=True, blank=True, verbose_name='Термін дії коду')

    password_reset_token = models.CharField(max_length=64, null=True, blank=True, verbose_name='Токен скидання пароля')
    password_reset_token_expires = models.DateTimeField(null=True, blank=True, verbose_name='Термін дії токена скидання')

    is_deleted = models.BooleanField(default=False, verbose_name='Видалено')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата видалення')

    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'Користувача'
        verbose_name_plural = 'Користувачі'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_full_name()} ({self.email})'

    def get_full_name(self):
        parts = [self.last_name, self.first_name]
        if self.patronymic:
            parts.append(self.patronymic)
        return ' '.join(parts).strip()

    @property
    def is_patient(self):
        return self.role == self.Role.PATIENT

    @property
    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN


class Patient(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='patient_profile',
        verbose_name='Користувач'
    )
    class Gender(models.TextChoices):
        MALE = 'male', 'Чоловік'
        FEMALE = 'female', 'Жінка'

    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата народження'
    )
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        blank=True,
        verbose_name='Стать'
    )

    class Meta:
        verbose_name = 'Пацієнта'
        verbose_name_plural = 'Пацієнти'

    def __str__(self):
        return f'Пацієнт: {self.user.get_full_name()}'

    def get_age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
