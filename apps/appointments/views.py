from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.utils import timezone

from apps.accounts.permissions import IsPatient, IsDoctor
from .models import Appointment, MedicalRecord
from .serializers import (
    AppointmentListSerializer,
    AppointmentDetailSerializer,
    AppointmentCreateSerializer,
    CompleteAppointmentSerializer,
    MedicalRecordSerializer,
)


class AppointmentListCreateView(generics.ListCreateAPIView):
    """
    GET /api/appointments/ — список своїх записів
    POST /api/appointments/ — створити новий запис (тільки patient)

    Patient бачить свої записи, Doctor бачить свої.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AppointmentCreateSerializer
        return AppointmentListSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Appointment.objects.select_related(
            'patient__user', 'doctor__user', 'doctor__specialty'
        )

        if user.is_patient:
            queryset = queryset.filter(patient=user.patient_profile)
        elif user.is_doctor:
            queryset = queryset.filter(doctor=user.doctor_profile)
        else:
            queryset = queryset.none()

        status_filter = self.request.query_params.get('status')
        if status_filter and status_filter in ['planned', 'completed', 'cancelled', 'missed']:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-date_time')

    def get_permissions(self):
        """POST тільки для пацієнтів, GET для всіх авторизованих."""
        if self.request.method == 'POST':
            return [IsPatient()]
        return [IsAuthenticated()]

    @extend_schema(
        summary='Список моїх записів',
        tags=['Записи'],
        parameters=[
            OpenApiParameter('status', description='Фільтр по статусу (planned/completed/cancelled/missed)')
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='Записатись до лікаря',
        tags=['Записи'],
        request=AppointmentCreateSerializer
    )
    def post(self, request, *args, **kwargs):
        serializer = AppointmentCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            appointment = serializer.save()

            self._notify_patient(appointment)

            return Response(
                AppointmentDetailSerializer(appointment, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _notify_patient(self, appointment):
        """Надсилаємо сповіщення пацієнту про підтвердження запису."""
        from apps.notifications.models import Notification
        dt_str = appointment.date_time.strftime('%d.%m.%Y о %H:%M')
        Notification.objects.create(
            user=appointment.patient.user,
            message=(
                f'Ваш запис до лікаря {appointment.doctor.get_full_name()} '
                f'({appointment.doctor.specialty.name}) підтверджено на {dt_str}.'
            ),
            link=f'/appointments/{appointment.id}/'
        )


class AppointmentDetailView(generics.RetrieveAPIView):
    """
    GET /api/appointments/{id}/
    Деталі запису на прийом.
    """
    serializer_class = AppointmentDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Appointment.objects.select_related(
            'patient__user', 'doctor__user', 'doctor__specialty'
        ).prefetch_related('medical_record')

        if user.is_patient:
            return queryset.filter(patient=user.patient_profile)
        elif user.is_doctor:
            return queryset.filter(doctor=user.doctor_profile)
        return queryset

    @extend_schema(summary='Деталі запису', tags=['Записи'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CancelAppointmentView(APIView):
    """
    PATCH /api/appointments/{id}/cancel/
    Скасування запису пацієнтом (тільки зі статусом planned).
    """
    permission_classes = [IsPatient]

    @extend_schema(summary='Скасувати запис', tags=['Записи'])
    def patch(self, request, pk):
        try:
            appointment = Appointment.objects.get(
                pk=pk,
                patient=request.user.patient_profile,
                status=Appointment.Status.PLANNED
            )
        except Appointment.DoesNotExist:
            return Response(
                {'error': 'Запис не знайдено або не може бути скасований.'},
                status=status.HTTP_404_NOT_FOUND
            )

        appointment.status = Appointment.Status.CANCELLED
        appointment.save()

        from apps.notifications.models import Notification
        dt_str = appointment.date_time.strftime('%d.%m.%Y о %H:%M')
        Notification.objects.create(
            user=appointment.doctor.user,
            message=(
                f'Пацієнт {appointment.patient.user.get_full_name()} '
                f'скасував запис на {dt_str}.'
            )
        )

        return Response({
            'message': 'Запис успішно скасовано.',
            'status': appointment.status
        })


class CompleteAppointmentView(APIView):
    """
    PATCH /api/appointments/{id}/complete/
    Завершення прийому лікарем + додавання медичної картки.
    """
    permission_classes = [IsDoctor]

    @extend_schema(
        summary='Завершити прийом',
        tags=['Записи'],
        request=CompleteAppointmentSerializer
    )
    def patch(self, request, pk):
        try:
            appointment = Appointment.objects.get(
                pk=pk,
                doctor=request.user.doctor_profile,
                status=Appointment.Status.PLANNED
            )
        except Appointment.DoesNotExist:
            return Response(
                {'error': 'Запис не знайдено або не може бути завершений.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CompleteAppointmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        appointment.status = Appointment.Status.COMPLETED
        appointment.save()

        MedicalRecord.objects.create(
            appointment=appointment,
            diagnosis=serializer.validated_data['diagnosis'],
            treatment=serializer.validated_data['treatment'],
            doctor_notes=serializer.validated_data.get('doctor_notes', '')
        )

        from apps.notifications.models import Notification
        Notification.objects.create(
            user=appointment.patient.user,
            message=(
                f'Ваш прийом у лікаря {appointment.doctor.get_full_name()} '
                f'завершено. Медичну картку можна переглянути в особистому кабінеті.'
            ),
            link=f'/appointments/{appointment.id}/'
        )

        return Response({
            'message': 'Прийом завершено. Медична картка збережена.',
            'appointment_id': appointment.id,
        })


class PublicStatsView(APIView):
    """
    GET /api/appointments/public-stats/
    Публічна статистика для головної сторінки.
    """
    permission_classes = [AllowAny]

    @extend_schema(summary='Публічна статистика', tags=['Записи'])
    def get(self, request):
        return Response({
            'completed_total': Appointment.objects.filter(
                status__in=[Appointment.Status.PLANNED, Appointment.Status.COMPLETED]
            ).count(),
        })


class AutoCancelExpiredView(APIView):
    """
    POST /api/appointments/auto-cancel/
    Автоматичне скасування прострочених записів пацієнта.
    Запис вважається простроченим якщо:
      date_time + slot_duration + 10 хвилин < зараз
    Викликається при завантаженні сторінки записів пацієнта.
    """
    permission_classes = [IsPatient]

    @extend_schema(summary='Авто-позначення пропущених записів', tags=['Записи'])
    def post(self, request):
        from datetime import timedelta
        from apps.notifications.models import Notification

        patient = request.user.patient_profile
        now = timezone.now()

        planned = Appointment.objects.filter(
            patient=patient,
            status=Appointment.Status.PLANNED,
        ).select_related('doctor__user', 'doctor__specialty')

        missed_ids = []
        for apt in planned:
            deadline = apt.date_time + timedelta(minutes=apt.doctor.slot_duration + 10)
            if deadline < now:
                apt.status = Appointment.Status.MISSED
                apt.save(update_fields=['status'])
                missed_ids.append(apt.id)

                dt_str = apt.date_time.strftime('%d.%m.%Y о %H:%M')
                Notification.objects.create(
                    user=request.user,
                    message=(
                        f'Ваш запис до лікаря {apt.doctor.get_full_name()} '
                        f'{dt_str} позначений як пропущений через неявку.'
                    ),
                    link=f'/appointments/{apt.id}/'
                )
                Notification.objects.create(
                    user=apt.doctor.user,
                    message=(
                        f'Пацієнт {request.user.get_full_name()} не з\'явився на прийом '
                        f'{dt_str}. Запис позначений як пропущений.'
                    ),
                    link=f'/appointments/{apt.id}/'
                )

        return Response({
            'missed_count': len(missed_ids),
            'missed_ids': missed_ids,
        })


class AutoCancelDoctorView(APIView):
    """
    POST /api/appointments/auto-cancel-doctor/
    Автоматичне скасування прострочених записів лікаря.
    Викликається при завантаженні сторінки /appointments/doctor/.
    Сповіщення отримують обидва: пацієнт і лікар.
    """
    permission_classes = [IsDoctor]

    @extend_schema(summary='Авто-позначення пропущених записів лікаря', tags=['Записи'])
    def post(self, request):
        from datetime import timedelta
        from apps.notifications.models import Notification

        doctor = request.user.doctor_profile
        now = timezone.now()

        planned = Appointment.objects.filter(
            doctor=doctor,
            status=Appointment.Status.PLANNED,
        ).select_related('patient__user')

        missed_ids = []
        for apt in planned:
            deadline = apt.date_time + timedelta(minutes=doctor.slot_duration + 10)
            if deadline < now:
                apt.status = Appointment.Status.MISSED
                apt.save(update_fields=['status'])
                missed_ids.append(apt.id)

                dt_str = apt.date_time.strftime('%d.%m.%Y о %H:%M')
                patient_name = apt.patient.user.get_full_name()
                Notification.objects.create(
                    user=apt.patient.user,
                    message=(
                        f'Ваш запис до лікаря {request.user.get_full_name()} '
                        f'{dt_str} позначений як пропущений через неявку.'
                    ),
                    link=f'/appointments/{apt.id}/'
                )
                Notification.objects.create(
                    user=request.user,
                    message=(
                        f'Пацієнт {patient_name} не з\'явився на прийом '
                        f'{dt_str}. Запис позначений як пропущений.'
                    ),
                    link=f'/appointments/{apt.id}/'
                )

        return Response({
            'missed_count': len(missed_ids),
            'missed_ids': missed_ids,
        })


class MedicalRecordsView(generics.ListAPIView):
    """
    GET /api/appointments/medical-records/
    Медична картка пацієнта — всі завершені записи з діагнозами.
    Тільки для пацієнтів.
    """
    serializer_class = AppointmentDetailSerializer
    permission_classes = [IsPatient]

    def get_queryset(self):
        return Appointment.objects.filter(
            patient=self.request.user.patient_profile,
            status=Appointment.Status.COMPLETED
        ).select_related(
            'doctor__user', 'doctor__specialty'
        ).prefetch_related('medical_record').order_by('-date_time')

    @extend_schema(summary='Моя медична картка', tags=['Записи'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
