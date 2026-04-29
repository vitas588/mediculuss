from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from apps.appointments.models import Appointment
from apps.notifications.models import Notification


class Command(BaseCommand):
    help = 'Надсилає нагадування пацієнтам та лікарям про завтрашні записи'

    def handle(self, *args, **options):
        tomorrow = date.today() + timedelta(days=1)
        self.stdout.write(f'Пошук записів на {tomorrow}...')

        appointments = Appointment.objects.filter(
            date_time__date=tomorrow,
            status=Appointment.Status.PLANNED
        ).select_related(
            'patient__user',
            'doctor__user',
            'doctor__specialty'
        )

        if not appointments.exists():
            self.stdout.write(self.style.WARNING('Немає записів на завтра.'))
            return

        self.stdout.write(f'Знайдено записів: {appointments.count()}')

        doctor_appointments = {}
        for apt in appointments:
            doctor = apt.doctor
            if doctor.id not in doctor_appointments:
                doctor_appointments[doctor.id] = {'doctor': doctor, 'count': 0}
            doctor_appointments[doctor.id]['count'] += 1

        patient_notifications = []
        for apt in appointments:
            time_str = apt.date_time.strftime('%H:%M')
            patient_notifications.append(Notification(
                user=apt.patient.user,
                message=(
                    f'Нагадування: завтра о {time_str} у вас прийом у лікаря '
                    f'{apt.doctor.get_full_name()} ({apt.doctor.specialty.name}).'
                ),
                link=f'/appointments/{apt.id}/'
            ))

        Notification.objects.bulk_create(patient_notifications)
        self.stdout.write(f'✓ Надіслано {len(patient_notifications)} нагадувань пацієнтам')

        doctor_notifications = []
        for doctor_id, info in doctor_appointments.items():
            doctor = info['doctor']
            count = info['count']
            doctor_notifications.append(Notification(
                user=doctor.user,
                message=(
                    f'Нагадування: завтра ({tomorrow.strftime("%d.%m.%Y")}) '
                    f'у вас заплановано {count} пацієнт(ів).'
                ),
                link='/appointments/doctor/'
            ))

        Notification.objects.bulk_create(doctor_notifications)
        self.stdout.write(f'✓ Надіслано {len(doctor_notifications)} нагадувань лікарям')
        self.stdout.write(self.style.SUCCESS('Нагадування успішно надіслані!'))
