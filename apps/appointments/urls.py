from django.urls import path
from .views import (
    AppointmentListCreateView,
    AppointmentDetailView,
    CancelAppointmentView,
    CompleteAppointmentView,
    MedicalRecordsView,
    PublicStatsView,
    AutoCancelExpiredView,
    AutoCancelDoctorView,
)

urlpatterns = [
    path('public-stats/', PublicStatsView.as_view(), name='appointment-public-stats'),

    path('auto-cancel/', AutoCancelExpiredView.as_view(), name='appointment-auto-cancel'),

    path('auto-cancel-doctor/', AutoCancelDoctorView.as_view(), name='appointment-auto-cancel-doctor'),

    path('', AppointmentListCreateView.as_view(), name='appointment-list-create'),

    path('medical-records/', MedicalRecordsView.as_view(), name='medical-records'),

    path('<int:pk>/', AppointmentDetailView.as_view(), name='appointment-detail'),

    path('<int:pk>/cancel/', CancelAppointmentView.as_view(), name='appointment-cancel'),

    path('<int:pk>/complete/', CompleteAppointmentView.as_view(), name='appointment-complete'),
]
