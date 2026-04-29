from django.contrib import admin
from django.utils.html import format_html
from .models import Doctor, Specialty, DoctorSchedule


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ['icon', 'name', 'slug', 'doctor_count']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

    @admin.display(description='Кількість лікарів')
    def doctor_count(self, obj):
        return obj.doctors.count()


class DoctorScheduleInline(admin.TabularInline):
    model = DoctorSchedule
    extra = 0
    fields = ['day_of_week', 'work_start', 'work_end', 'is_working']


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = [
        'get_full_name', 'specialty',
        'experience_years', 'slot_duration', 'is_active'
    ]
    list_display_links = ['get_full_name']
    list_filter = ['specialty', 'is_active', 'experience_years']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    list_editable = ['is_active']
    inlines = [DoctorScheduleInline]

    fieldsets = (
        ('Основна інформація', {
            'fields': ('user', 'specialty', 'photo', 'is_active')
        }),
        ('Деталі', {
            'fields': ('experience_years', 'slot_duration', 'description')
        }),
    )

    @admin.display(description='Фото')
    def get_photo_thumbnail(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;border-radius:50%;object-fit:cover;">',
                obj.photo.url
            )
        return '—'

    @admin.display(description='Повне ім\'я')
    def get_full_name(self, obj):
        return obj.get_full_name()


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'get_day_name', 'work_start', 'work_end', 'is_working']
    list_filter = ['day_of_week', 'is_working']
    search_fields = ['doctor__user__first_name', 'doctor__user__last_name']
    list_editable = ['is_working']

    @admin.display(description='День тижня')
    def get_day_name(self, obj):
        return obj.get_day_of_week_display()
