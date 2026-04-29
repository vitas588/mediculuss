from rest_framework.permissions import BasePermission


class IsPatient(BasePermission):
    message = 'Доступ тільки для пацієнтів.'

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'patient'
        )


class IsDoctor(BasePermission):
    message = 'Доступ тільки для лікарів.'

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'doctor'
        )


class IsAdmin(BasePermission):
    message = 'Доступ тільки для адміністраторів.'

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'admin' or request.user.is_staff)
        )


class IsPatientOrDoctor(BasePermission):
    message = 'Доступ для пацієнтів та лікарів.'

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['patient', 'doctor']
        )


class IsOwnerOrAdmin(BasePermission):
    message = 'Доступ тільки для власника або адміністратора.'

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin' or request.user.is_staff:
            return True
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return obj == request.user
