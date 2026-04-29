from django.contrib import admin
from django.utils.html import format_html
from .models import Appointment, MedicalRecord


class MedicalRecordInline(admin.StackedInline):
    model = MedicalRecord
    extra = 0
    fields = ['diagnosis', 'treatment', 'doctor_notes', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'get_patient_name', 'get_doctor_name',
        'date_time', 'get_status_badge', 'created_at'
    ]
    list_filter = ['status', 'date_time', 'doctor__specialty']
    search_fields = [
        'patient__user__first_name', 'patient__user__last_name',
        'doctor__user__first_name', 'doctor__user__last_name'
    ]
    date_hierarchy = 'date_time'
    list_select_related = ['patient__user', 'doctor__user', 'doctor__specialty']
    inlines = [MedicalRecordInline]

    fieldsets = (
        ('Основна інформація', {
            'fields': ('patient', 'doctor', 'date_time', 'status')
        }),
        ('Додатково', {
            'fields': ('reason', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']

    @admin.display(description='Пацієнт')
    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name()

    @admin.display(description='Лікар')
    def get_doctor_name(self, obj):
        return obj.doctor.get_full_name()

    @admin.display(description='Статус')
    def get_status_badge(self, obj):
        colors = {
            'planned': '#0d6efd',
            'completed': '#198754',
            'cancelled': '#dc3545',
            'missed': '#fd7e14',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color:white;background:{};padding:2px 8px;border-radius:4px;">{}</span>',
            color,
            obj.get_status_display()
        )


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_patient', 'get_doctor', 'get_date', 'created_at']
    search_fields = [
        'appointment__patient__user__first_name',
        'appointment__patient__user__last_name',
        'diagnosis'
    ]
    readonly_fields = ['created_at']

    @admin.display(description='Пацієнт')
    def get_patient(self, obj):
        return obj.appointment.patient.user.get_full_name()

    @admin.display(description='Лікар')
    def get_doctor(self, obj):
        return obj.appointment.doctor.get_full_name()

    @admin.display(description='Дата прийому')
    def get_date(self, obj):
        return obj.appointment.date_time.strftime('%d.%m.%Y %H:%M')
