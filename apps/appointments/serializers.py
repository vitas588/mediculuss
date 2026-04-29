from rest_framework import serializers
from django.utils import timezone
from .models import Appointment, MedicalRecord


class MedicalRecordSerializer(serializers.ModelSerializer):

    class Meta:
        model = MedicalRecord
        fields = ['id', 'diagnosis', 'treatment', 'doctor_notes', 'created_at']
        read_only_fields = ['id', 'created_at']


class MedicalRecordCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = MedicalRecord
        fields = ['diagnosis', 'treatment', 'doctor_notes']


class AppointmentListSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='patient.user.get_full_name',
        read_only=True
    )
    doctor_id = serializers.IntegerField(source='doctor.id', read_only=True)
    doctor_name = serializers.SerializerMethodField()
    specialty_name = serializers.CharField(
        source='doctor.specialty.name',
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    has_medical_record = serializers.SerializerMethodField()
    doctor_photo_url = serializers.SerializerMethodField()
    slot_duration = serializers.IntegerField(source='doctor.slot_duration', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient_name', 'doctor_id', 'doctor_name', 'specialty_name',
            'doctor_photo_url', 'slot_duration',
            'date_time', 'status', 'status_display',
            'reason', 'created_at', 'has_medical_record'
        ]

    def get_doctor_name(self, obj):
        return obj.doctor.get_full_name()

    def get_has_medical_record(self, obj):
        return hasattr(obj, 'medical_record')

    def get_doctor_photo_url(self, obj):
        request = self.context.get('request')
        if obj.doctor.photo and request:
            return request.build_absolute_uri(obj.doctor.photo.url)
        return None


class AppointmentDetailSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='patient.user.get_full_name',
        read_only=True
    )
    patient_phone = serializers.CharField(
        source='patient.user.phone',
        read_only=True
    )
    doctor_id = serializers.IntegerField(source='doctor.id', read_only=True)
    doctor_name = serializers.SerializerMethodField()
    doctor_specialty = serializers.CharField(
        source='doctor.specialty.name',
        read_only=True
    )
    doctor_photo = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    medical_record = MedicalRecordSerializer(read_only=True)
    is_cancellable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient_name', 'patient_phone',
            'doctor_id', 'doctor_name', 'doctor_specialty', 'doctor_photo',
            'date_time', 'status', 'status_display',
            'reason', 'created_at', 'is_cancellable', 'medical_record'
        ]

    def get_doctor_name(self, obj):
        return obj.doctor.get_full_name()

    def get_doctor_photo(self, obj):
        request = self.context.get('request')
        if obj.doctor.photo and request:
            return request.build_absolute_uri(obj.doctor.photo.url)
        return None


class AppointmentCreateSerializer(serializers.ModelSerializer):
    doctor_id = serializers.IntegerField(write_only=True)
    date_time = serializers.DateTimeField()

    class Meta:
        model = Appointment
        fields = ['doctor_id', 'date_time', 'reason']

    def validate_date_time(self, value):
        from datetime import timedelta, date
        today = timezone.now().date()

        if value < timezone.now():
            raise serializers.ValidationError(
                'Час запису має бути в майбутньому.'
            )

        max_date = today + timedelta(days=14)
        if value.date() > max_date:
            raise serializers.ValidationError(
                'Запис можливий тільки на найближчі 14 днів.'
            )

        return value

    def validate(self, data):
        from apps.doctors.models import Doctor

        try:
            doctor = Doctor.objects.get(pk=data['doctor_id'], is_active=True)
        except Doctor.DoesNotExist:
            raise serializers.ValidationError({'doctor_id': 'Лікаря не знайдено або він не приймає.'})

        is_booked = Appointment.objects.filter(
            doctor=doctor,
            date_time=data['date_time'],
            status__in=['planned', 'completed']
        ).exists()

        if is_booked:
            raise serializers.ValidationError(
                {'date_time': 'Цей час вже зайнятий. Оберіть інший.'}
            )

        from apps.doctors.models import DoctorSchedule
        target_date = data['date_time'].date()
        day_of_week = target_date.weekday()

        try:
            schedule = DoctorSchedule.objects.get(
                doctor=doctor,
                day_of_week=day_of_week,
                is_working=True
            )
        except DoctorSchedule.DoesNotExist:
            raise serializers.ValidationError(
                {'date_time': 'Лікар не приймає в цей день тижня.'}
            )

        appointment_time = data['date_time'].time()
        if appointment_time < schedule.work_start or appointment_time >= schedule.work_end:
            raise serializers.ValidationError(
                {'date_time': f'Лікар приймає з {schedule.work_start} до {schedule.work_end}.'}
            )

        from django.core.exceptions import ObjectDoesNotExist
        user = self.context['request'].user
        try:
            patient = user.patient_profile
        except ObjectDoesNotExist:
            patient = None

        if patient:
            target_date = data['date_time'].date()

            planned_count = Appointment.objects.filter(
                patient=patient,
                doctor=doctor,
                status=Appointment.Status.PLANNED,
            ).count()
            if planned_count >= 2:
                raise serializers.ValidationError(
                    'Ви вже маєте 2 активні записи до цього лікаря. '
                    'Скасуйте один із записів щоб записатись знову.'
                )

            same_date = Appointment.objects.filter(
                patient=patient,
                doctor=doctor,
                date_time__date=target_date,
                status=Appointment.Status.PLANNED,
            ).exists()
            if same_date:
                raise serializers.ValidationError(
                    {'date_time': 'У вас вже є запис до цього лікаря на цю дату.'}
                )

        data['doctor'] = doctor
        return data

    def create(self, validated_data):
        from apps.accounts.models import Patient

        validated_data.pop('doctor_id')
        user = self.context['request'].user

        from django.core.exceptions import ObjectDoesNotExist
        try:
            patient = user.patient_profile
        except ObjectDoesNotExist:
            patient, _ = Patient.objects.get_or_create(user=user)

        appointment = Appointment.objects.create(
            patient=patient,
            **validated_data
        )
        return appointment


class CompleteAppointmentSerializer(serializers.Serializer):
    diagnosis = serializers.CharField(help_text='Діагноз')
    treatment = serializers.CharField(help_text='Призначення / лікування')
    doctor_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Приватні нотатки лікаря'
    )
