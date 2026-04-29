from datetime import date, datetime, timedelta
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.accounts.permissions import IsDoctor
from .models import Doctor, Specialty, DoctorSchedule
from .serializers import (
    DoctorListSerializer,
    DoctorDetailSerializer,
    DoctorPhotoSerializer,
    DoctorScheduleSerializer,
    SpecialtySerializer,
    AvailableSlotSerializer,
)


class DoctorPagination(PageNumberPagination):
    """Пагінація для списку лікарів — 9 на сторінку."""
    page_size = 9
    page_size_query_param = 'page_size'


class SpecialtyListView(generics.ListAPIView):
    """
    GET /api/doctors/specialties/
    Спеціальності, де є хоча б один активний лікар (is_active=True).
    Публічний ендпоінт. Без пагінації — список невеликий.
    """
    serializer_class = SpecialtySerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Specialty.objects.filter(
            doctors__is_active=True,
        ).distinct()

    @extend_schema(summary='Список спеціальностей', tags=['Лікарі'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DoctorListView(generics.ListAPIView):
    """
    GET /api/doctors/
    Список лікарів з пошуком та фільтрацією.
    Фільтри: specialty (slug), search (ім'я/прізвище).
    Виключає лікарів без жодного робочого дня в розкладі.
    """
    serializer_class = DoctorListSerializer
    permission_classes = [AllowAny]
    pagination_class = DoctorPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['specialty__slug', 'is_active']
    search_fields = ['user__first_name', 'user__last_name', 'specialty__name']

    def get_queryset(self):
        queryset = Doctor.objects.filter(
            is_active=True,
            schedules__is_working=True
        ).distinct().select_related('user', 'specialty')
        specialty = self.request.query_params.get('specialty')
        if specialty:
            queryset = queryset.filter(specialty__slug=specialty)
        return queryset

    @extend_schema(
        summary='Список лікарів',
        tags=['Лікарі'],
        parameters=[
            OpenApiParameter('specialty', description='Slug спеціальності', required=False),
            OpenApiParameter('search', description='Пошук по імені/прізвищу', required=False),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DoctorDetailView(generics.RetrieveAPIView):
    """
    GET /api/doctors/{id}/
    Детальний профіль лікаря.
    """
    queryset = Doctor.objects.select_related('user', 'specialty').prefetch_related('schedules')
    serializer_class = DoctorDetailSerializer
    permission_classes = [AllowAny]

    @extend_schema(summary='Профіль лікаря', tags=['Лікарі'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DoctorAvailableSlotsView(APIView):
    """
    GET /api/doctors/{id}/available-slots/?date=YYYY-MM-DD
    Повертає список вільних часових слотів лікаря на вказану дату.

    Алгоритм генерації слотів:
    1. Беремо розклад лікаря на цей день тижня
    2. Генеруємо слоти від work_start до work_end з кроком slot_duration
    3. Видаляємо вже зайняті слоти (Appointment зі статусом planned/completed)
    4. Повертаємо тільки вільні слоти
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Вільні слоти лікаря',
        tags=['Лікарі'],
        parameters=[
            OpenApiParameter('date', description='Дата у форматі YYYY-MM-DD', required=True)
        ]
    )
    def get(self, request, pk):
        try:
            doctor = Doctor.objects.get(pk=pk, is_active=True)
        except Doctor.DoesNotExist:
            return Response({'error': 'Лікаря не знайдено.'}, status=status.HTTP_404_NOT_FOUND)

        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'error': 'Параметр date обов\'язковий.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Невірний формат дати. Використовуйте YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        today = date.today()
        max_date = today + timedelta(days=14)

        if target_date < today:
            return Response({'error': 'Запис можливий тільки на сьогодні або пізніше.'}, status=status.HTTP_400_BAD_REQUEST)
        if target_date > max_date:
            return Response({'error': 'Запис можливий тільки на найближчі 14 днів.'}, status=status.HTTP_400_BAD_REQUEST)

        day_of_week = target_date.weekday()

        try:
            schedule = DoctorSchedule.objects.get(
                doctor=doctor,
                day_of_week=day_of_week,
                is_working=True
            )
        except DoctorSchedule.DoesNotExist:
            return Response({
                'slots': [],
                'message': 'Лікар не приймає в цей день.'
            })

        slots = []
        current_time = datetime.combine(target_date, schedule.work_start)
        end_time = datetime.combine(target_date, schedule.work_end)
        slot_delta = timedelta(minutes=doctor.slot_duration)

        while current_time + slot_delta <= end_time:
            slots.append(current_time)
            current_time += slot_delta

        from apps.appointments.models import Appointment
        booked_times = Appointment.objects.filter(
            doctor=doctor,
            date_time__date=target_date,
            status__in=['planned', 'completed']
        ).values_list('date_time', flat=True)

        booked_naive = set()
        for bt in booked_times:
            if timezone.is_aware(bt):
                bt = timezone.localtime(bt).replace(tzinfo=None)
            booked_naive.add(bt)

        if target_date == today:
            now = datetime.now()
            slots = [s for s in slots if s > now]

        available_slots = []
        for slot_dt in slots:
            is_booked = slot_dt in booked_naive
            if not is_booked:
                available_slots.append({
                    'time': slot_dt.strftime('%H:%M'),
                    'datetime': slot_dt.strftime('%Y-%m-%dT%H:%M:%S'),
                    'is_available': True
                })

        return Response({
            'date': date_str,
            'doctor': doctor.get_full_name(),
            'slot_duration': doctor.slot_duration,
            'slots': available_slots
        })


class DoctorPhotoUploadView(APIView):
    """
    PUT    /api/doctors/me/photo/ — завантаження/оновлення фото
    DELETE /api/doctors/me/photo/ — видалення фото
    Тільки для авторизованих лікарів.
    """
    permission_classes = [IsDoctor]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary='Завантажити фото лікаря',
        tags=['Лікарі'],
        request=DoctorPhotoSerializer,
    )
    def put(self, request):
        try:
            doctor = request.user.doctor_profile
        except Doctor.DoesNotExist:
            return Response({'error': 'Профіль лікаря не знайдено.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DoctorPhotoSerializer(doctor, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            photo_url = doctor.photo.url if doctor.photo else None
            return Response({
                'message': 'Фото успішно оновлено.',
                'photo_url': photo_url
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary='Видалити фото лікаря', tags=['Лікарі'])
    def delete(self, request):
        try:
            doctor = request.user.doctor_profile
        except Doctor.DoesNotExist:
            return Response({'error': 'Профіль лікаря не знайдено.'}, status=status.HTTP_404_NOT_FOUND)

        if doctor.photo:
            doctor.photo.delete(save=False)
            doctor.photo = None
            doctor.save(update_fields=['photo'])

        return Response({'message': 'Фото успішно видалено.'}, status=status.HTTP_200_OK)


class DoctorMeView(generics.RetrieveAPIView):
    """
    GET /api/doctors/me/
    Власний профіль лікаря (для сторінки профілю).
    """
    serializer_class = DoctorDetailSerializer
    permission_classes = [IsDoctor]

    def get_object(self):
        return Doctor.objects.select_related(
            'user', 'specialty'
        ).prefetch_related('schedules').get(user=self.request.user)

    @extend_schema(summary='Мій профіль лікаря', tags=['Лікарі'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DoctorMyScheduleView(generics.ListAPIView):
    """
    GET /api/doctors/me/schedule/
    Власний розклад лікаря.
    """
    serializer_class = DoctorScheduleSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return DoctorSchedule.objects.filter(doctor=self.request.user.doctor_profile)

    @extend_schema(summary='Мій розклад', tags=['Лікарі'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
