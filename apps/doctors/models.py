from django.db import models
from django.utils.text import slugify
from cloudinary.models import CloudinaryField
from apps.accounts.models import User


class Specialty(models.Model):
    name = models.CharField(max_length=100, verbose_name='Назва спеціальності')
    icon = models.CharField(
        max_length=50,
        default='🏥',
        verbose_name='Іконка (emoji або Bootstrap Icons клас)'
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name='URL-slug'
    )
    description = models.TextField(blank=True, verbose_name='Опис')

    class Meta:
        verbose_name = 'Спеціальність'
        verbose_name_plural = 'Спеціальності'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Doctor(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='doctor_profile',
        verbose_name='Користувач'
    )
    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.SET_NULL,
        null=True,
        related_name='doctors',
        verbose_name='Спеціальність'
    )
    experience_years = models.PositiveIntegerField(
        default=0,
        verbose_name='Досвід роботи (років)'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Опис / про лікаря'
    )
    photo = CloudinaryField(
        'image',
        blank=True,
        null=True,
        verbose_name='Фото'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Приймає пацієнтів'
    )
    slot_duration = models.PositiveIntegerField(
        default=30,
        verbose_name='Тривалість прийому (хв)'
    )

    class Meta:
        verbose_name = 'Лікаря'
        verbose_name_plural = 'Лікарі'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f'Лікар {self.user.get_full_name()} ({self.specialty})'

    def get_full_name(self):
        return self.user.get_full_name()

    def get_photo_url(self):
        if self.photo:
            return self.photo.url
        return None


class DoctorSchedule(models.Model):
    DAY_CHOICES = [
        (0, 'Понеділок'),
        (1, 'Вівторок'),
        (2, 'Середа'),
        (3, 'Четвер'),
        (4, 'П\'ятниця'),
        (5, 'Субота'),
        (6, 'Неділя'),
    ]

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='Лікар'
    )
    day_of_week = models.IntegerField(
        choices=DAY_CHOICES,
        verbose_name='День тижня'
    )
    work_start = models.TimeField(verbose_name='Початок роботи')
    work_end = models.TimeField(verbose_name='Кінець роботи')
    is_working = models.BooleanField(
        default=True,
        verbose_name='Робочий день'
    )

    class Meta:
        verbose_name = 'Розклад лікаря'
        verbose_name_plural = 'Розклади лікарів'
        unique_together = ['doctor', 'day_of_week']
        ordering = ['day_of_week']

    def __str__(self):
        day_name = dict(self.DAY_CHOICES).get(self.day_of_week, '')
        status = 'Робочий' if self.is_working else 'Вихідний'
        return f'{self.doctor.get_full_name()} — {day_name} ({status})'
