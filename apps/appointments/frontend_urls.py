from django.urls import path
from .frontend_views import (
    AppointmentListPageView,
    AppointmentDetailPageView,
    DoctorAppointmentsPageView,
)

urlpatterns = [
    path('', AppointmentListPageView.as_view(), name='appointments-page'),

    path('doctor/', DoctorAppointmentsPageView.as_view(), name='doctor-appointments-page'),

    path('<int:pk>/', AppointmentDetailPageView.as_view(), name='appointment-detail-page'),
]
