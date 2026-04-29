from django.db import models
from django.db.models import Q
from django.utils import timezone
from apps.accounts.models import Patient
from apps.doctors.models import Doctor


class Appointment(models.Model):

    class Status(models.TextChoices):
        PLANNED = 'planned', 'Заплановано'
        COMPLETED = 'completed', 'Завершено'
        CANCELLED = 'cancelled', 'Скасовано'
        MISSED = 'missed', 'Пропущено'

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name='Пацієнт'
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name='Лікар'
    )
    date_time = models.DateTimeField(verbose_name='Дата та час прийому')
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PLANNED,
        verbose_name='Статус'
    )
    reason = models.TextField(
        blank=True,
        verbose_name='Причина звернення'
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата створення'
    )

    class Meta:
        verbose_name = 'Запис на прийом'
        verbose_name_plural = 'Записи на прийом'
        ordering = ['-date_time']
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'date_time'],
                condition=~Q(status__in=['cancelled', 'missed']),
                name='unique_active_appointment'
            )
        ]

    def __str__(self):
        return (
            f'{self.patient.user.get_full_name()} → '
            f'{self.doctor.get_full_name()} '
            f'({self.date_time.strftime("%d.%m.%Y %H:%M")})'
        )

    @property
    def is_cancellable(self):
        return self.status == self.Status.PLANNED

    @property
    def is_completable(self):
        return self.status == self.Status.PLANNED


class MedicalRecord(models.Model):
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='medical_record',
        verbose_name='Запис на прийом'
    )
    diagnosis = models.TextField(verbose_name='Діагноз')
    treatment = models.TextField(verbose_name='Призначення / лікування')
    doctor_notes = models.TextField(
        blank=True,
        verbose_name='Приватні нотатки лікаря'
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата заповнення'
    )

    class Meta:
        verbose_name = 'Результат прийому'
        verbose_name_plural = 'Результати прийому'
        ordering = ['-created_at']

    def __str__(self):
        return f'Результат: {self.appointment}'
