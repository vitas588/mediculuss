from django.urls import path
from .frontend_views import DoctorListPageView, DoctorDetailPageView, DoctorCabinetView

urlpatterns = [
    path('', DoctorListPageView.as_view(), name='doctor-list-page'),

    path('cabinet/', DoctorCabinetView.as_view(), name='doctor-cabinet'),

    path('<int:pk>/', DoctorDetailPageView.as_view(), name='doctor-detail-page'),
]
