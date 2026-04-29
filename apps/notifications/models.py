from django.db import models
from django.utils import timezone
from apps.accounts.models import User


class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Користувач'
    )
    message = models.TextField(verbose_name='Повідомлення')
    is_read = models.BooleanField(
        default=False,
        verbose_name='Прочитано'
    )
    link = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Посилання (URL кнопки "переглянути")'
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата створення'
    )

    class Meta:
        verbose_name = 'Сповіщення'
        verbose_name_plural = 'Сповіщення'
        ordering = ['-created_at']

    def __str__(self):
        status = 'прочитано' if self.is_read else 'нове'
        return f'[{status}] {self.user.email}: {self.message[:50]}...'
