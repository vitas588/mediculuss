from django.contrib import admin
from django.urls import path, include
from . import admin_config
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/auth/', include('apps.accounts.urls')),
    path('api/doctors/', include('apps.doctors.urls')),
    path('api/appointments/', include('apps.appointments.urls')),
    path('api/notifications/', include('apps.notifications.urls')),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    path('', include('apps.accounts.frontend_urls')),
    path('doctors/', include('apps.doctors.frontend_urls')),
    path('appointments/', include('apps.appointments.frontend_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
