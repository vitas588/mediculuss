from django.views.generic import TemplateView
from .models import Doctor, Specialty


class DoctorListPageView(TemplateView):
    """Сторінка списку лікарів."""
    template_name = 'doctors/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['specialties'] = Specialty.objects.all()
        return context


class DoctorDetailPageView(TemplateView):
    """Сторінка профілю лікаря."""
    template_name = 'doctors/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doctor_id'] = kwargs.get('pk')
        return context


class DoctorCabinetView(TemplateView):
    """Кабінет лікаря (тільки для role=doctor)."""
    template_name = 'doctors/cabinet.html'
