from rest_framework import serializers
from .models import Doctor, Specialty, DoctorSchedule


class SpecialtySerializer(serializers.ModelSerializer):

    class Meta:
        model = Specialty
        fields = ['id', 'name', 'icon', 'slug', 'description']


class DoctorScheduleSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = DoctorSchedule
        fields = ['id', 'day_of_week', 'day_name', 'work_start', 'work_end', 'is_working']


class DoctorListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    specialty_name = serializers.CharField(source='specialty.name', read_only=True)
    specialty_slug = serializers.CharField(source='specialty.slug', read_only=True)
    specialty_icon = serializers.CharField(source='specialty.icon', read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            'id', 'full_name', 'specialty_name', 'specialty_slug',
            'specialty_icon', 'experience_years', 'photo_url', 'is_active', 'slot_duration'
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_photo_url(self, obj):
        if obj.photo:
            return obj.photo.url
        return None


class DoctorDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.CharField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    specialty = SpecialtySerializer(read_only=True)
    schedules = DoctorScheduleSerializer(many=True, read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            'id', 'full_name', 'email', 'phone',
            'specialty', 'experience_years', 'description',
            'photo_url', 'is_active', 'slot_duration', 'schedules'
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_photo_url(self, obj):
        if obj.photo:
            return obj.photo.url
        return None


class DoctorPhotoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Doctor
        fields = ['photo']

    def validate_photo(self, value):
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError('Розмір фото не може перевищувати 5 МБ.')
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if hasattr(value, 'content_type') and value.content_type not in allowed_types:
            raise serializers.ValidationError('Дозволені формати: JPEG, PNG, WebP.')
        return value


class AvailableSlotSerializer(serializers.Serializer):
    time = serializers.TimeField(format='%H:%M')
    datetime = serializers.DateTimeField()
    is_available = serializers.BooleanField()
