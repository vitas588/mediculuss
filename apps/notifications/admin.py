from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['get_user', 'get_short_message', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'message']
    list_editable = ['is_read']
    date_hierarchy = 'created_at'

    @admin.display(description='Користувач')
    def get_user(self, obj):
        return obj.user.get_full_name()

    @admin.display(description='Повідомлення')
    def get_short_message(self, obj):
        return obj.message[:80] + '...' if len(obj.message) > 80 else obj.message
