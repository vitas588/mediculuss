import re
import random
import string
import secrets
import threading
from datetime import timedelta
from django.core.mail import send_mail, EmailMessage
from django.conf import settings as django_settings
from django.utils import timezone
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import User, Patient
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    ProfileSerializer,
    UserSerializer
)


def _generate_code():
    """Generate a random 6-digit verification code."""
    return ''.join(random.choices(string.digits, k=6))


def send_email_async(subject, body, from_email, to_list, html=False):
    def _send():
        try:
            if html:
                msg = EmailMessage()
                msg.subject = subject
                msg.body = body
                msg.from_email = from_email
                msg.to = to_list
                msg.content_subtype = 'html'
                msg.send()
            else:
                send_mail(subject, body, from_email, to_list, fail_silently=True)
        except Exception:
            pass
    thread = threading.Thread(target=_send, daemon=True)
    thread.start()


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Реєстрація нового пацієнта.
    Публічний ендпоінт.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(description='Успішна реєстрація'),
            400: OpenApiResponse(description='Помилка валідації'),
        },
        summary='Реєстрація пацієнта',
        tags=['Авторизація']
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            code = _generate_code()
            user.email_verification_code = code
            user.email_verification_code_expires = timezone.now() + timedelta(minutes=5)
            user.email_verified = False
            user.save(update_fields=['email_verification_code', 'email_verification_code_expires', 'email_verified'])

            send_email_async(
                subject='Підтвердження email — Mediculus',
                body=(
                    f'Вітаємо, {user.first_name}!\n\n'
                    f'Ваш код підтвердження: {code}\n\n'
                    f'Код дійсний 5 хвилин.\n\n'
                    f'Якщо ви не реєструвались — проігноруйте цей лист.'
                ),
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                to_list=[user.email],
            )

            return Response({
                'message': 'Реєстрація успішна! Перевірте email для підтвердження акаунту.',
                'requires_verification': True,
                'email': user.email,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginThrottle(AnonRateThrottle):
    """Обмеження кількості спроб входу: 5 на хвилину."""
    rate = '5/min'

    def throttle_failure(self):
        return False


class LoginView(APIView):
    """
    POST /api/auth/login/
    Вхід в систему. Повертає access + refresh токени.
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description='Успішний вхід з токенами'),
            400: OpenApiResponse(description='Невірні дані'),
        },
        summary='Вхід в систему',
        tags=['Авторизація']
    )
    def throttled(self, request, wait):
        """Кастомне повідомлення при перевищенні ліміту."""
        from rest_framework.exceptions import Throttled
        raise Throttled(detail='Забагато спроб входу. Спробуйте через 1 хвилину.')

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']

            if not user.email_verified:
                return Response({
                    'error': 'email_not_verified',
                    'message': 'Ваш акаунт не підтверджено. Перевірте пошту або надішліть код повторно.',
                    'email': user.email,
                }, status=status.HTTP_403_FORBIDDEN)

            remember_me = request.data.get('remember_me', False)
            refresh = RefreshToken.for_user(user)
            if remember_me:
                refresh.set_exp(lifetime=timedelta(days=30))

            return Response({
                'message': f'Ласкаво просимо, {user.get_full_name()}!',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.get_full_name(),
                    'role': user.role,
                },
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                }
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Вихід з системи. Додає refresh токен до blacklist.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Вихід з системи',
        tags=['Авторизація']
    )
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh токен обов\'язковий.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Ви успішно вийшли з системи.'}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({'error': 'Невірний токен.'}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/auth/profile/ — перегляд свого профілю
    PUT  /api/auth/profile/ — оновлення телефону (ім'я/прізвище/email не змінюються)
    PATCH /api/auth/profile/ — часткове оновлення
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    @extend_schema(summary='Мій профіль', tags=['Профіль'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(summary='Оновити профіль', tags=['Профіль'])
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(summary='Часткове оновлення профілю', tags=['Профіль'])
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def get_object(self):
        """Повертає поточного авторизованого користувача."""
        return self.request.user


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    Зміна пароля користувача.
    Потрібен старий пароль для підтвердження.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Зміна пароля', tags=['Профіль'])
    def post(self, request):
        old_password = request.data.get('old_password', '')
        new_password = request.data.get('new_password', '')
        new_password_confirm = request.data.get('new_password_confirm', '')

        if not old_password or not new_password or not new_password_confirm:
            return Response(
                {'error': 'Всі поля обов\'язкові.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not request.user.check_password(old_password):
            return Response(
                {'error': 'Невірний поточний пароль.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != new_password_confirm:
            return Response(
                {'error': 'Нові паролі не співпадають.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 8:
            return Response(
                {'error': 'Пароль має містити мінімум 8 символів.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not any(c.isalpha() for c in new_password):
            return Response(
                {'error': 'Пароль має містити хоча б одну літеру.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not any(c.isdigit() for c in new_password):
            return Response(
                {'error': 'Пароль має містити хоча б одну цифру.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.set_password(new_password)
        request.user.save()

        return Response({'message': 'Пароль успішно змінено.'}, status=status.HTTP_200_OK)


class VerifyEmailView(APIView):
    """POST /api/auth/verify-email/ — verify email with 6-digit code."""
    permission_classes = [AllowAny]

    @extend_schema(summary='Підтвердження email', tags=['Авторизація'])
    def post(self, request):
        email = request.data.get('email', '').lower().strip()
        code = request.data.get('code', '').strip()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Користувача не знайдено.'}, status=status.HTTP_404_NOT_FOUND)

        if user.email_verified:
            return Response({'message': 'Email вже підтверджено. Можете увійти.'})

        if not user.email_verification_code:
            return Response({'error': 'Код підтвердження не знайдено. Запросіть новий.'}, status=status.HTTP_400_BAD_REQUEST)

        if timezone.now() > user.email_verification_code_expires:
            return Response({'error': 'Код прострочений. Надішліть новий.'}, status=status.HTTP_400_BAD_REQUEST)

        if user.email_verification_code != code:
            return Response({'error': 'Невірний код підтвердження.'}, status=status.HTTP_400_BAD_REQUEST)

        user.email_verified = True
        user.email_verification_code = None
        user.email_verification_code_expires = None
        user.save(update_fields=['email_verified', 'email_verification_code', 'email_verification_code_expires'])

        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Email успішно підтверджено!',
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.get_full_name(),
                'role': user.role,
            },
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_200_OK)


class ResendVerificationView(APIView):
    """POST /api/auth/resend-verification/ — resend verification code."""
    permission_classes = [AllowAny]

    @extend_schema(summary='Повторне надсилання коду', tags=['Авторизація'])
    def post(self, request):
        email = request.data.get('email', '').lower().strip()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': 'Якщо такий email існує, код надіслано повторно.'})

        if user.email_verified:
            return Response({'message': 'Email вже підтверджено. Можете увійти.'})

        code = _generate_code()
        user.email_verification_code = code
        user.email_verification_code_expires = timezone.now() + timedelta(minutes=5)
        user.save(update_fields=['email_verification_code', 'email_verification_code_expires'])

        send_email_async(
            subject='Підтвердження email — Mediculus',
            body=(
                f'Ваш новий код підтвердження: {code}\n\n'
                f'Код дійсний 5 хвилин.'
            ),
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to_list=[user.email],
        )

        return Response({'message': 'Код надіслано повторно. Перевірте пошту.'})


class ForgotPasswordView(APIView):
    """POST /api/auth/forgot-password/ — send password reset email."""
    permission_classes = [AllowAny]

    @extend_schema(summary='Запит на відновлення пароля', tags=['Авторизація'])
    def post(self, request):
        email = request.data.get('email', '').lower().strip()

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response({'message': 'Лист з інструкціями для відновлення паролю надіслано на вашу пошту.'})

        token = secrets.token_hex(32)
        user.password_reset_token = token
        user.password_reset_token_expires = timezone.now() + timedelta(hours=1)
        user.save(update_fields=['password_reset_token', 'password_reset_token_expires'])

        base_url = request.build_absolute_uri('/').rstrip('/')
        reset_url = f'{base_url}/reset-password/{token}/'

        send_email_async(
            subject='Відновлення пароля — Mediculus',
            body=(
                f'Для відновлення пароля перейдіть за посиланням:\n'
                f'{reset_url}\n\n'
                f'Посилання дійсне 1 годину.\n\n'
                f'Якщо ви не запитували відновлення — проігноруйте цей лист.'
            ),
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to_list=[user.email],
        )

        return Response({'message': 'Лист з інструкціями для відновлення паролю надіслано на вашу пошту.'})


class ResetPasswordView(APIView):
    """
    GET  /api/auth/reset-password/?token=xxx — перевірка валідності токена
    POST /api/auth/reset-password/           — зміна пароля за токеном
    """
    permission_classes = [AllowAny]

    @extend_schema(summary='Перевірка токена скидання пароля', tags=['Авторизація'])
    def get(self, request):
        token = request.query_params.get('token', '').strip()
        if not token:
            return Response({'valid': False, 'error': 'Токен обов\'язковий.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(password_reset_token=token)
        except User.DoesNotExist:
            return Response({'valid': False, 'error': 'Посилання недійсне або вже використане.'})

        if not user.password_reset_token_expires or timezone.now() > user.password_reset_token_expires:
            return Response({'valid': False, 'error': 'Посилання застаріло. Запросіть нове відновлення пароля.'})

        return Response({'valid': True})

    @extend_schema(summary='Скидання пароля', tags=['Авторизація'])
    def post(self, request):
        token = request.data.get('token', '').strip()
        new_password = request.data.get('new_password', '')
        new_password_confirm = request.data.get('new_password_confirm', '')

        if not token:
            return Response({'error': 'Токен обов\'язковий.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(password_reset_token=token)
        except User.DoesNotExist:
            return Response({'error': 'Посилання недійсне або вже використане.'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.password_reset_token_expires or timezone.now() > user.password_reset_token_expires:
            return Response({'error': 'Посилання застаріло. Запросіть нове відновлення пароля.'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({'error': 'Пароль має містити мінімум 8 символів.'}, status=status.HTTP_400_BAD_REQUEST)
        if not any(c.isalpha() for c in new_password):
            return Response({'error': 'Пароль має містити хоча б одну літеру.'}, status=status.HTTP_400_BAD_REQUEST)
        if not any(c.isdigit() for c in new_password):
            return Response({'error': 'Пароль має містити хоча б одну цифру.'}, status=status.HTTP_400_BAD_REQUEST)
        if new_password != new_password_confirm:
            return Response({'error': 'Паролі не співпадають.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.password_reset_token = None
        user.password_reset_token_expires = None
        user.save()

        return Response({'message': 'Пароль успішно змінено. Тепер ви можете увійти.'})


class DeleteAccountView(APIView):
    """POST /api/auth/delete-account/ — soft delete patient account."""
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Видалення акаунту', tags=['Профіль'])
    def post(self, request):
        password = request.data.get('password', '')

        if not request.user.check_password(password):
            return Response({'error': 'Невірний пароль.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user_id = user.id

        user.is_deleted = True
        user.deleted_at = timezone.now()
        user.is_active = False
        user.first_name = 'Видалений'
        user.last_name = 'користувач'
        user.patronymic = ''
        user.phone = ''
        user.email = f'deleted_{user_id}@deleted.com'
        user.save()

        return Response({'message': 'Акаунт успішно видалено.'})
