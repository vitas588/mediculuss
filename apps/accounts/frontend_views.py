from django.views.generic import TemplateView
from django.utils import timezone
from apps.accounts.models import User, Patient
from apps.doctors.models import Doctor
from apps.appointments.models import Appointment
import calendar
from datetime import date


class HomeView(TemplateView):
    """Головна сторінка лікарні (публічна)."""
    template_name = 'home.html'


class LoginPageView(TemplateView):
    """Сторінка входу."""
    template_name = 'accounts/login.html'


class RegisterPageView(TemplateView):
    """Сторінка реєстрації."""
    template_name = 'accounts/register.html'


class ProfilePageView(TemplateView):
    """Особистий кабінет (залежно від ролі)."""
    template_name = 'accounts/profile.html'


class AboutPageView(TemplateView):
    """Сторінка 'Про Mediculus'."""
    template_name = 'about.html'


class VerifyEmailPageView(TemplateView):
    template_name = 'accounts/verify-email.html'


class ForgotPasswordPageView(TemplateView):
    template_name = 'accounts/forgot-password.html'


class ResetPasswordPageView(TemplateView):
    template_name = 'accounts/reset-password.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['token'] = kwargs.get('token', '')
        return context


class PrivacyPolicyPageView(TemplateView):
    template_name = 'privacy-policy.html'


class AdminPanelView(TemplateView):
    """
    Панель статистики адміністратора.
    GET /admin-panel/
    """
    template_name = 'admin_panel/dashboard.html'

    def get_context_data(self, **kwargs):
        """Передаємо статистику в шаблон."""
        context = super().get_context_data(**kwargs)

        context['stats'] = {
            'patients_count': Patient.objects.count(),
            'doctors_count': Doctor.objects.filter(is_active=True).count(),
            'appointments_total': Appointment.objects.count(),
            'appointments_planned': Appointment.objects.filter(status='planned').count(),
            'appointments_completed': Appointment.objects.filter(status='completed').count(),
            'appointments_cancelled': Appointment.objects.filter(status='cancelled').count(),
            'appointments_missed': Appointment.objects.filter(status='missed').count(),
        }

        from django.db.models import Count
        from django.db.models.functions import TruncDay, TruncWeek, TruncMonth

        now = timezone.now()
        year = now.year
        month = now.month

        MONTHS_UK = ['Січ', 'Лют', 'Бер', 'Кві', 'Тра', 'Чер',
                     'Лип', 'Сер', 'Вер', 'Жов', 'Лис', 'Гру']

        monthly_qs = (
            Appointment.objects
            .filter(date_time__year=year)
            .annotate(m=TruncMonth('date_time'))
            .values('m')
            .annotate(count=Count('id'))
            .order_by('m')
        )
        monthly_counts = {item['m'].month: item['count'] for item in monthly_qs}
        context['monthly_labels'] = [f'{MONTHS_UK[m - 1]} {year}' for m in range(1, 13)]
        context['monthly_data'] = [monthly_counts.get(m, 0) for m in range(1, 13)]

        weekly_qs = (
            Appointment.objects
            .filter(date_time__year=year)
            .annotate(w=TruncWeek('date_time'))
            .values('w')
            .annotate(count=Count('id'))
            .order_by('w')
        )
        context['weekly_labels'] = [item['w'].strftime('%d.%m') for item in weekly_qs]
        context['weekly_data'] = [item['count'] for item in weekly_qs]

        daily_qs = (
            Appointment.objects
            .filter(date_time__year=year, date_time__month=month)
            .annotate(d=TruncDay('date_time'))
            .values('d')
            .annotate(count=Count('id'))
            .order_by('d')
        )
        daily_counts = {item['d'].date(): item['count'] for item in daily_qs}
        days_in_month = calendar.monthrange(year, month)[1]
        context['daily_labels'] = [f'{d:02d}.{month:02d}' for d in range(1, days_in_month + 1)]
        context['daily_data'] = [
            daily_counts.get(date(year, month, d), 0) for d in range(1, days_in_month + 1)
        ]

        return context
