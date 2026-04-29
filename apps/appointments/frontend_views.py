from django.views.generic import TemplateView


class AppointmentListPageView(TemplateView):
    """Сторінка списку записів пацієнта."""
    template_name = 'appointments/list.html'


class AppointmentDetailPageView(TemplateView):
    """Сторінка деталей запису."""
    template_name = 'appointments/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appointment_id'] = kwargs.get('pk')
        return context


class DoctorAppointmentsPageView(TemplateView):
    """Сторінка записів для лікаря."""
    template_name = 'appointments/doctor_list.html'
