from django.urls import path
from .frontend_views import (
    HomeView,
    LoginPageView,
    RegisterPageView,
    ProfilePageView,
    AboutPageView,
    AdminPanelView,
    VerifyEmailPageView,
    ForgotPasswordPageView,
    ResetPasswordPageView,
    PrivacyPolicyPageView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),

    path('login/', LoginPageView.as_view(), name='login'),
    path('register/', RegisterPageView.as_view(), name='register'),

    path('profile/', ProfilePageView.as_view(), name='profile'),

    path('about/', AboutPageView.as_view(), name='about'),

    path('admin-panel/', AdminPanelView.as_view(), name='admin-panel'),

    path('verify-email/', VerifyEmailPageView.as_view(), name='verify-email'),

    path('forgot-password/', ForgotPasswordPageView.as_view(), name='forgot-password'),
    path('reset-password/<str:token>/', ResetPasswordPageView.as_view(), name='reset-password'),

    path('privacy-policy/', PrivacyPolicyPageView.as_view(), name='privacy-policy'),
]
