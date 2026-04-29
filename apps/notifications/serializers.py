from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'message', 'is_read', 'link', 'created_at', 'time_ago']
        read_only_fields = ['id', 'message', 'link', 'created_at']

    def get_time_ago(self, obj):
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        diff = now - obj.created_at

        if diff < timedelta(minutes=1):
            return 'Щойно'
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f'{minutes} хв тому'
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f'{hours} год тому'
        elif diff < timedelta(days=7):
            days = diff.days
            return f'{days} дн тому'
        else:
            return obj.created_at.strftime('%d.%m.%Y')
