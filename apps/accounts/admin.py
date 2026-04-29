from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Patient


@admin.register(User)
class UserAdmin(BaseUserAdmin):

    list_display = [
        'email', 'get_full_name', 'role', 'phone',
        'is_active', 'is_staff', 'created_at'
    ]
    list_filter = ['role', 'is_active', 'is_staff', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']

    fieldsets = (
        ('Основна інформація', {
            'fields': ('email', 'password')
        }),
        ('Персональні дані', {
            'fields': ('first_name', 'last_name', 'patronymic', 'phone')
        }),
        ('Роль та права', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Дати', {
            'fields': ('created_at', 'last_login'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'patronymic', 'phone', 'role', 'password1', 'password2'),
        }),
    )

    readonly_fields = ['created_at', 'last_login']

    @admin.display(description='Повне ім\'я')
    def get_full_name(self, obj):
        return obj.get_full_name()


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):

    list_display = ['get_full_name', 'get_email', 'date_of_birth', 'get_age', 'gender']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    list_filter = ['date_of_birth']

    @admin.display(description='Повне ім\'я')
    def get_full_name(self, obj):
        return obj.user.get_full_name()

    @admin.display(description='Email')
    def get_email(self, obj):
        return obj.user.email

    @admin.display(description='Вік')
    def get_age(self, obj):
        age = obj.get_age()
        return f'{age} р.' if age else '—'
