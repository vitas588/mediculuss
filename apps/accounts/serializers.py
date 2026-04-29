from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Patient


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='Мінімум 8 символів'
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text='Підтвердження пароля'
    )
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=Patient.Gender.choices,
        required=False,
        allow_blank=True
    )

    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'patronymic', 'phone',
            'date_of_birth', 'gender'
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError('Користувач з таким email вже існує.')
        return value.lower()

    def validate(self, data):
        password = data['password']
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Паролі не співпадають.'})
        if len(password) < 8:
            raise serializers.ValidationError({'password': 'Пароль має містити мінімум 8 символів.'})
        if not any(c.isalpha() for c in password):
            raise serializers.ValidationError({'password': 'Пароль має містити хоча б одну літеру.'})
        if not any(c.isdigit() for c in password):
            raise serializers.ValidationError({'password': 'Пароль має містити хоча б одну цифру.'})
        return data

    def create(self, validated_data):
        from django.db import transaction

        date_of_birth = validated_data.pop('date_of_birth', None)
        gender = validated_data.pop('gender', '')
        validated_data.pop('password_confirm')

        with transaction.atomic():
            user = User.objects.create_user(
                role=User.Role.PATIENT,
                **validated_data
            )

            Patient.objects.get_or_create(
                user=user,
                defaults={
                    'date_of_birth': date_of_birth,
                    'gender': gender or '',
                }
            )

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, data):
        email = data.get('email', '').lower()
        password = data.get('password')

        user = authenticate(request=self.context.get('request'), email=email, password=password)

        if not user:
            raise serializers.ValidationError('Невірний email або пароль.')
        if not user.is_active:
            raise serializers.ValidationError('Акаунт деактивовано. Зверніться до адміністратора.')

        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'patronymic', 'full_name', 'phone', 'role', 'created_at']
        read_only_fields = ['id', 'email', 'role', 'created_at']

    def get_full_name(self, obj):
        return obj.get_full_name()


class PatientProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    age = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = ['id', 'user', 'date_of_birth', 'gender', 'age']

    def get_age(self, obj):
        return obj.get_age()


class ProfileSerializer(serializers.ModelSerializer):
    patient_profile = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'patronymic', 'full_name',
            'phone', 'role', 'created_at', 'patient_profile'
        ]
        read_only_fields = ['id', 'email', 'role', 'created_at']

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_patient_profile(self, obj):
        if obj.is_patient and hasattr(obj, 'patient_profile'):
            profile = obj.patient_profile
            return {
                'date_of_birth': profile.date_of_birth,
                'gender': profile.gender,
                'gender_display': profile.get_gender_display() if profile.gender else '',
                'age': profile.get_age()
            }
        return None

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.patronymic = validated_data.get('patronymic', instance.patronymic)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.save()
        return instance
