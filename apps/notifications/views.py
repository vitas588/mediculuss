from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """
    GET /api/notifications/
    Список своїх сповіщень (від нових до старих).
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @extend_schema(summary='Мої сповіщення', tags=['Сповіщення'])
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        unread_count = queryset.filter(is_read=False).count()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'unread_count': unread_count,
            'notifications': serializer.data
        })


class MarkNotificationReadView(APIView):
    """
    PATCH /api/notifications/{id}/read/
    Позначити сповіщення як прочитане.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Позначити як прочитане', tags=['Сповіщення'])
    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({'error': 'Сповіщення не знайдено.'}, status=status.HTTP_404_NOT_FOUND)

        notification.is_read = True
        notification.save()
        return Response({'message': 'Сповіщення позначено як прочитане.'})


class MarkAllNotificationsReadView(APIView):
    """
    PATCH /api/notifications/read-all/
    Позначити всі сповіщення як прочитані.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Позначити всі як прочитані', tags=['Сповіщення'])
    def patch(self, request):
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)

        return Response({
            'message': f'Позначено {count} сповіщень як прочитані.'
        })
