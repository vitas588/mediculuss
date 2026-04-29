from django.urls import path
from .views import (
    DoctorListView,
    DoctorDetailView,
    DoctorAvailableSlotsView,
    SpecialtyListView,
    DoctorPhotoUploadView,
    DoctorMeView,
    DoctorMyScheduleView,
)

urlpatterns = [
    path('specialties/', SpecialtyListView.as_view(), name='specialty-list'),

    path('', DoctorListView.as_view(), name='doctor-list'),

    path('<int:pk>/', DoctorDetailView.as_view(), name='doctor-detail'),

    path('<int:pk>/available-slots/', DoctorAvailableSlotsView.as_view(), name='doctor-slots'),

    path('me/', DoctorMeView.as_view(), name='doctor-me'),

    path('me/photo/', DoctorPhotoUploadView.as_view(), name='doctor-photo'),

    path('me/schedule/', DoctorMyScheduleView.as_view(), name='doctor-schedule'),
]
