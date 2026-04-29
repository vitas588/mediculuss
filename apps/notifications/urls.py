from django.urls import path
from .views import (
    NotificationListView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),

    path('read-all/', MarkAllNotificationsReadView.as_view(), name='notification-read-all'),

    path('<int:pk>/read/', MarkNotificationReadView.as_view(), name='notification-read'),
]
