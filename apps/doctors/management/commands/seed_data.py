from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, time, date, datetime


class Command(BaseCommand):
    help = 'Seed the database with test data: specialties, doctors, patients, appointments'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true',
                            help='Delete all existing test data before seeding')

    def handle(self, *args, **options):
        if options['flush']:
            self._flush_data()
        self.stdout.write('Заповнення бази даних тестовими даними...\n')
        self._create_specialties()
        self._create_admin()
        self._create_doctors()
        self._create_patients()
        self._create_appointments()
        self._print_accounts()
        self.stdout.write(self.style.SUCCESS('\n✅ Тестові дані успішно створені!\n'))

    def _flush_data(self):
        from apps.appointments.models import Appointment, MedicalRecord
        from apps.notifications.models import Notification
        from apps.doctors.models import Doctor, Specialty, DoctorSchedule
        from apps.accounts.models import User, Patient

        self.stdout.write('Видалення існуючих даних...')
        Notification.objects.all().delete()
        MedicalRecord.objects.all().delete()
        Appointment.objects.all().delete()
        DoctorSchedule.objects.all().delete()
        Doctor.objects.all().delete()
        Patient.objects.all().delete()
        User.objects.filter(role__in=[User.Role.DOCTOR, User.Role.PATIENT]).delete()
        User.objects.filter(email='admin@mediculus.ua').delete()
        Specialty.objects.all().delete()
        self.stdout.write(self.style.WARNING('✓ Дані видалено\n'))

    def _create_specialties(self):
        from apps.doctors.models import Specialty

        rows = [
            ('Терапевт',            '🩺',      'terapevt',     'Загальна медицина та первинна допомога'),
            ('Кардіолог',           '❤️',       'kardiolog',    'Захворювання серця та судин'),
            ('Невролог',            '🧠',      'nevrolog',     'Захворювання нервової системи'),
            ('Офтальмолог',         '👁️',       'oftalmolog',   'Захворювання очей та зору'),
            ('Педіатр',             '👶',      'pediatr',      'Медицина для дітей та підлітків'),
            ('Хірург',              '🔬',      'khirurg',      'Хірургічні втручання та операції'),
            ('Психолог',            '💭',      'psykholog',    'Психологічна допомога та консультації'),
            ('Стоматолог',          '🦷',      'stomatolog',   'Лікування зубів та ротової порожнини'),
            ('Вірусолог',           '🦠',      'virusolog',    'Діагностика та лікування вірусних інфекцій'),
            ('Ортопед',             '🦴',      'ortoped',      'Захворювання опорно-рухового апарату'),
            ('Дерматолог',          '🧴',      'dermatoloh',   'Захворювання шкіри, волосся та нігтів'),
            ('Ендокринолог',        '💊',      'endokrynolog', 'Захворювання ендокринної системи'),
            ('Уролог',              '🏥',      'urolog',       'Захворювання сечовивідної системи'),
            ('Гінеколог',           '👩‍⚕️', 'hinekoloh', "Жіноче здоров'я та гінекологія"),
            ('Отоларинголог (ЛОР)', '👂',      'lor',          'Захворювання вуха, горла та носа'),
        ]
        for name, icon, slug, desc in rows:
            Specialty.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'icon': icon, 'description': desc},
            )
        self.specialties = {s.slug: s for s in Specialty.objects.all()}
        self.stdout.write(f'✓ Спеціальності: {len(rows)}')

    def _create_admin(self):
        from apps.accounts.models import User

        user, created = User.objects.get_or_create(
            email='admin@mediculus.ua',
            defaults={
                'first_name': 'Віталій',
                'last_name': 'Денисенко',
                'patronymic': 'Анатолійович',
                'phone': '+380501000000',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
                'email_verified': True,
            },
        )
        if created:
            user.set_password('Denysenko2026!')
            user.save()
        elif not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])
        self.stdout.write('✓ Адміністратор: admin@mediculus.ua')

    _DOCTORS_DATA = [
        {
            'email': 'o.kovalenko@gmail.com', 'password': 'Kovalenko2026!',
            'first_name': 'Олена', 'last_name': 'Коваленко', 'patronymic': 'Василівна',
            'phone': '+380661000001', 'specialty': 'terapevt', 'experience_years': 15,
            'description': (
                'Досвідчений терапевт з 15-річним стажем у сфері загальної медицини. '
                'Спеціалізується на лікуванні гострих респіраторних захворювань, '
                'артеріальної гіпертензії та цукрового діабету. '
                'Застосовує індивідуальний підхід та сучасні протоколи лікування.'
            ),
        },
        {
            'email': 'v.shevchenko@gmail.com', 'password': 'Shevchenko2026!',
            'first_name': 'Василь', 'last_name': 'Шевченко', 'patronymic': 'Андрійович',
            'phone': '+380661000002', 'specialty': 'oftalmolog', 'experience_years': 12,
            'description': (
                'Офтальмолог із 12-річним досвідом лікування захворювань органів зору. '
                'Спеціалізується на корекції міопії, далекозорості та астигматизму, '
                'а також лікуванні глаукоми та катаракти. '
                'Виконує мікрохірургічні операції на очах.'
            ),
        },
        {
            'email': 'n.ivanenko@gmail.com', 'password': 'Ivanenko2026!',
            'first_name': 'Наталія', 'last_name': 'Іваненко', 'patronymic': 'Петрівна',
            'phone': '+380661000003', 'specialty': 'nevrolog', 'experience_years': 20,
            'description': (
                'Невролог вищої категорії з 20-річним клінічним досвідом. '
                'Спеціалізується на лікуванні мігрені, епілепсії та нейродегенеративних захворювань. '
                'Проводить ЕЕГ та ультразвукове дослідження судин головного мозку.'
            ),
        },
        {
            'email': 'o.bondarenko@gmail.com', 'password': 'Bondarenko2026!',
            'first_name': 'Олексій', 'last_name': 'Бондаренко', 'patronymic': 'Миколайович',
            'phone': '+380661000004', 'specialty': 'kardiolog', 'experience_years': 18,
            'description': (
                'Кардіолог вищої категорії, кандидат медичних наук, з 18-річним досвідом. '
                'Спеціалізується на ішемічній хворобі серця, аритміях та серцевій недостатності. '
                'Проводить ехокардіографію та добове моніторування ЕКГ.'
            ),
        },
        {
            'email': 'i.melnyk@gmail.com', 'password': 'Melnyk2026!',
            'first_name': 'Ірина', 'last_name': 'Мельник', 'patronymic': 'Сергіївна',
            'phone': '+380661000005', 'specialty': 'pediatr', 'experience_years': 10,
            'description': (
                'Педіатр з 10-річним досвідом роботи з дітьми від народження до 18 років. '
                'Спеціалізується на лікуванні дитячих інфекцій, алергологічних станів '
                'та порушень розвитку. Проводить планові огляди та вакцинацію.'
            ),
        },
        {
            'email': 'a.kravchenko@gmail.com', 'password': 'Kravchenko2026!',
            'first_name': 'Андрій', 'last_name': 'Кравченко', 'patronymic': 'Васильович',
            'phone': '+380661000006', 'specialty': 'khirurg', 'experience_years': 22,
            'description': (
                'Хірург вищої категорії з 22-річним досвідом планових та екстрених втручань. '
                "Спеціалізується на абдомінальній хірургії, лікуванні гриж та жовчнокам'яної хвороби. "
                'Виконує класичні та лапароскопічні операції.'
            ),
        },
        {
            'email': 't.polishchuk@gmail.com', 'password': 'Polishchuk2026!',
            'first_name': 'Тетяна', 'last_name': 'Поліщук', 'patronymic': 'Олегівна',
            'phone': '+380661000007', 'specialty': 'psykholog', 'experience_years': 8,
            'description': (
                'Клінічний психолог з 8-річним досвідом роботи з дорослими та підлітками. '
                'Спеціалізується на КПТ, лікуванні тривожних розладів, депресії та ПТСР. '
                'Проводить індивідуальні та групові сеанси психотерапії.'
            ),
        },
        {
            'email': 'd.savchenko@gmail.com', 'password': 'Savchenko2026!',
            'first_name': 'Дмитро', 'last_name': 'Савченко', 'patronymic': 'Іванович',
            'phone': '+380661000008', 'specialty': 'stomatolog', 'experience_years': 14,
            'description': (
                'Лікар-стоматолог з 14-річним досвідом терапевтичної та естетичної стоматології. '
                'Спеціалізується на лікуванні карієсу, пульпіту та пародонтиту. '
                'Використовує сучасні матеріали та безболісні методи лікування.'
            ),
        },
        {
            'email': 'o.lysenko@gmail.com', 'password': 'Lysenko2026!',
            'first_name': 'Ольга', 'last_name': 'Лисенко', 'patronymic': 'Михайлівна',
            'phone': '+380661000009', 'specialty': 'virusolog', 'experience_years': 11,
            'description': (
                'Лікар-вірусолог з 11-річним досвідом діагностики та лікування вірусних захворювань. '
                'Спеціалізується на гепатитах B і C, герпесвірусних інфекціях та ВІЛ-асоційованих станах. '
                'Проводить ПЛР-діагностику та підбір противірусної терапії.'
            ),
        },
        {
            'email': 'm.hrytsenko@gmail.com', 'password': 'Hrytsenko2026!',
            'first_name': 'Максим', 'last_name': 'Гриценко', 'patronymic': 'Олександрович',
            'phone': '+380661000010', 'specialty': 'ortoped', 'experience_years': 16,
            'description': (
                'Лікар-ортопед вищої категорії з 16-річним досвідом. '
                'Спеціалізується на артрозах великих суглобів, міжхребцевих грижах та сколіозі. '
                "Проводить ін'єкційну терапію та призначає індивідуальні програми реабілітації."
            ),
        },
        {
            'email': 's.romanenko@gmail.com', 'password': 'Romanenko2026!',
            'first_name': 'Світлана', 'last_name': 'Романенко', 'patronymic': 'Юріївна',
            'phone': '+380661000011', 'specialty': 'dermatoloh', 'experience_years': 9,
            'description': (
                'Лікар-дерматолог з 9-річним досвідом лікування шкірних захворювань. '
                'Спеціалізується на псоріазі, екземі, акне та алергічних дерматитах. '
                'Проводить дерматоскопію та призначає комплексне місцеве і системне лікування.'
            ),
        },
        {
            'email': 'v.tkachenko@gmail.com', 'password': 'Tkachenko2026!',
            'first_name': 'Віктор', 'last_name': 'Ткаченко', 'patronymic': 'Павлович',
            'phone': '+380661000012', 'specialty': 'endokrynolog', 'experience_years': 17,
            'description': (
                'Ендокринолог вищої категорії з 17-річним клінічним досвідом. '
                'Спеціалізується на цукровому діабеті, захворюваннях щитоподібної залози '
                'та порушеннях обміну речовин. Проводить УЗД щитоподібної залози.'
            ),
        },
        {
            'email': 'o.marchenko@gmail.com', 'password': 'Marchenko2026!',
            'first_name': 'Оксана', 'last_name': 'Марченко', 'patronymic': 'Леонідівна',
            'phone': '+380661000013', 'specialty': 'urolog', 'experience_years': 13,
            'description': (
                'Лікар-уролог з 13-річним досвідом лікування захворювань сечовивідної системи. '
                "Спеціалізується на сечокам'яній хворобі, циститі та простатиті. "
                'Виконує цистоскопію та ультразвукове дослідження нирок.'
            ),
        },
        {
            'email': 'l.zakharenko@gmail.com', 'password': 'Zakharenko2026!',
            'first_name': 'Людмила', 'last_name': 'Захаренко', 'patronymic': 'Григорівна',
            'phone': '+380661000014', 'specialty': 'hinekoloh', 'experience_years': 19,
            'description': (
                'Акушер-гінеколог вищої категорії з 19-річним досвідом. '
                "Спеціалізується на гінекологічних захворюваннях, веденні вагітності та плануванні сім'ї. "
                'Проводить УЗД органів малого тазу та кольпоскопію.'
            ),
        },
        {
            'email': 's.fedorenko@gmail.com', 'password': 'Fedorenko2026!',
            'first_name': 'Сергій', 'last_name': 'Федоренко', 'patronymic': 'Миколайович',
            'phone': '+380661000015', 'specialty': 'lor', 'experience_years': 11,
            'description': (
                'Лікар-отоларинголог з 11-річним досвідом лікування захворювань вуха, горла та носа. '
                'Спеціалізується на хронічних тонзилітах, синуситах та алергічних ринітах. '
                'Проводить ендоскопічне дослідження ЛОР-органів та мікрооперації.'
            ),
        },
        {
            'email': 'h.pavlenko@gmail.com', 'password': 'Pavlenko2026!',
            'first_name': 'Галина', 'last_name': 'Павленко', 'patronymic': 'Василівна',
            'phone': '+380661000016', 'specialty': 'terapevt', 'experience_years': 7,
            'description': (
                'Терапевт з 7-річним досвідом надання первинної допомоги дорослим пацієнтам. '
                'Спеціалізується на серцево-судинних захворюваннях та хворобах органів дихання. '
                'Проводить диспансеризацію та моніторинг хронічних захворювань.'
            ),
        },
        {
            'email': 'm.rudenko@gmail.com', 'password': 'Rudenko2026!',
            'first_name': 'Микола', 'last_name': 'Руденко', 'patronymic': 'Андрійович',
            'phone': '+380661000017', 'specialty': 'kardiolog', 'experience_years': 25,
            'description': (
                'Кардіолог-аритмолог, доктор медичних наук, з 25-річним досвідом. '
                'Спеціалізується на складних порушеннях серцевого ритму та кардіоміопатіях. '
                'Проводить добове моніторування ЕКГ та стрес-ехокардіографію.'
            ),
        },
        {
            'email': 'yu.bilous@gmail.com', 'password': 'Bilous2026!',
            'first_name': 'Юлія', 'last_name': 'Білоус', 'patronymic': 'Олексіївна',
            'phone': '+380661000018', 'specialty': 'pediatr', 'experience_years': 6,
            'description': (
                'Педіатр з 6-річним досвідом роботи з дітьми різного віку. '
                'Спеціалізується на профілактичній педіатрії, вакцинації '
                'та ранньому виявленні порушень розвитку. '
                'Активно застосовує принципи доказової медицини.'
            ),
        },
        {
            'email': 'i.horbachenko@gmail.com', 'password': 'Horbachenko2026!',
            'first_name': 'Ігор', 'last_name': 'Горбаченко', 'patronymic': 'Степанович',
            'phone': '+380661000019', 'specialty': 'khirurg', 'experience_years': 21,
            'description': (
                'Хірург вищої категорії з 21-річним досвідом торакальної та абдомінальної хірургії. '
                'Спеціалізується на лікуванні гострих хірургічних захворювань та травм. '
                'Майстерно виконує лапароскопічні операції на органах черевної порожнини.'
            ),
        },
        {
            'email': 'v.nechyporenko@gmail.com', 'password': 'Nechyporenko2026!',
            'first_name': 'Вікторія', 'last_name': 'Нечипоренко', 'patronymic': 'Дмитрівна',
            'phone': '+380661000020', 'specialty': 'nevrolog', 'experience_years': 14,
            'description': (
                'Невролог з 14-річним досвідом лікування захворювань нервової системи. '
                'Спеціалізується на вертеброневрології, нейропатіях та хронічному болю. '
                'Застосовує блокади, мануальну терапію та рефлексотерапію у комплексному лікуванні.'
            ),
        },
    ]

    def _create_doctors(self):
        from apps.accounts.models import User
        from apps.doctors.models import Doctor, DoctorSchedule

        self.doctors = []
        for d in self._DOCTORS_DATA:
            user, created = User.objects.get_or_create(
                email=d['email'],
                defaults={
                    'first_name': d['first_name'],
                    'last_name': d['last_name'],
                    'patronymic': d['patronymic'],
                    'phone': d['phone'],
                    'role': User.Role.DOCTOR,
                    'is_active': True,
                    'email_verified': True,
                },
            )
            if created:
                user.set_password(d['password'])
                user.save()
            elif not user.email_verified:
                user.email_verified = True
                user.save(update_fields=['email_verified'])

            doctor, _ = Doctor.objects.get_or_create(
                user=user,
                defaults={
                    'specialty': self.specialties[d['specialty']],
                    'experience_years': d['experience_years'],
                    'description': d['description'],
                    'slot_duration': 30,
                    'is_active': True,
                },
            )
            self.doctors.append(doctor)
            self._create_schedule(doctor)

        self.stdout.write(f'✓ Лікарі: {len(self.doctors)} з розкладами')

    def _create_schedule(self, doctor):
        from apps.doctors.models import DoctorSchedule

        for day in range(5):
            DoctorSchedule.objects.get_or_create(
                doctor=doctor, day_of_week=day,
                defaults={'work_start': time(9, 0), 'work_end': time(17, 0), 'is_working': True},
            )
        DoctorSchedule.objects.get_or_create(
            doctor=doctor, day_of_week=5,
            defaults={'work_start': time(10, 0), 'work_end': time(14, 0), 'is_working': True},
        )
        DoctorSchedule.objects.get_or_create(
            doctor=doctor, day_of_week=6,
            defaults={'work_start': time(9, 0), 'work_end': time(18, 0), 'is_working': False},
        )

    _PATIENTS_DATA = [
        {
            'email': 'vitalii.denysenko@gmail.com', 'password': 'Denysenko2026!',
            'first_name': 'Віталій', 'last_name': 'Денисенко', 'patronymic': 'Анатолійович',
            'phone': '+380501000001', 'gender': 'male', 'date_of_birth': date(2004, 1, 15),
        },
        {
            'email': 'maria.petrenko@gmail.com', 'password': 'Petrenko2026!',
            'first_name': 'Марія', 'last_name': 'Петренко', 'patronymic': 'Іванівна',
            'phone': '+380501000002', 'gender': 'female', 'date_of_birth': date(1990, 5, 23),
        },
        {
            'email': 'ivan.sydorenko@gmail.com', 'password': 'Sydorenko2026!',
            'first_name': 'Іван', 'last_name': 'Сидоренко', 'patronymic': 'Олегович',
            'phone': '+380501000003', 'gender': 'male', 'date_of_birth': date(1985, 11, 7),
        },
        {
            'email': 'oksana.kovalchuk@gmail.com', 'password': 'Kovalchuk2026!',
            'first_name': 'Оксана', 'last_name': 'Ковальчук', 'patronymic': 'Василівна',
            'phone': '+380501000004', 'gender': 'female', 'date_of_birth': date(1995, 3, 14),
        },
        {
            'email': 'andrii.moroz@gmail.com', 'password': 'Moroz2026!',
            'first_name': 'Андрій', 'last_name': 'Мороз', 'patronymic': 'Петрович',
            'phone': '+380501000005', 'gender': 'male', 'date_of_birth': date(1978, 8, 30),
        },
        {
            'email': 'kateryna.bilyk@gmail.com', 'password': 'Bilyk2026!',
            'first_name': 'Катерина', 'last_name': 'Білик', 'patronymic': 'Миколаївна',
            'phone': '+380501000006', 'gender': 'female', 'date_of_birth': date(2000, 12, 25),
        },
        {
            'email': 'oleh.kharchenko@gmail.com', 'password': 'Kharchenko2026!',
            'first_name': 'Олег', 'last_name': 'Харченко', 'patronymic': 'Вікторович',
            'phone': '+380501000007', 'gender': 'male', 'date_of_birth': date(1970, 4, 18),
        },
        {
            'email': 'natalia.levchenko@gmail.com', 'password': 'Levchenko2026!',
            'first_name': 'Наталія', 'last_name': 'Левченко', 'patronymic': 'Сергіївна',
            'phone': '+380501000008', 'gender': 'female', 'date_of_birth': date(1988, 7, 9),
        },
        {
            'email': 'mykhailo.diachenko@gmail.com', 'password': 'Diachenko2026!',
            'first_name': 'Михайло', 'last_name': 'Дяченко', 'patronymic': 'Романович',
            'phone': '+380501000009', 'gender': 'male', 'date_of_birth': date(1992, 2, 28),
        },
        {
            'email': 'olena.tymchenko@gmail.com', 'password': 'Tymchenko2026!',
            'first_name': 'Олена', 'last_name': 'Тимченко', 'patronymic': 'Борисівна',
            'phone': '+380501000010', 'gender': 'female', 'date_of_birth': date(1975, 6, 15),
        },
    ]

    def _create_patients(self):
        from apps.accounts.models import User, Patient

        self.patients = []
        for p in self._PATIENTS_DATA:
            user, created = User.objects.get_or_create(
                email=p['email'],
                defaults={
                    'first_name': p['first_name'],
                    'last_name': p['last_name'],
                    'patronymic': p['patronymic'],
                    'phone': p['phone'],
                    'role': User.Role.PATIENT,
                    'is_active': True,
                    'email_verified': True,
                },
            )
            if created:
                user.set_password(p['password'])
                user.save()
            elif not user.email_verified:
                user.email_verified = True
                user.save(update_fields=['email_verified'])

            patient, _ = Patient.objects.get_or_create(
                user=user,
                defaults={
                    'date_of_birth': p['date_of_birth'],
                    'gender': p['gender'],
                },
            )
            self.patients.append(patient)

        self.stdout.write(f'✓ Пацієнти: {len(self.patients)}')

    def _workday(self, d, forward=True):
        if d.weekday() == 6:
            d += timedelta(days=1) if forward else timedelta(days=-1)
        return d

    def _make_dt(self, d, h, m=0):
        return timezone.make_aware(datetime.combine(d, time(h, m)))

    def _create_appointments(self):
        from apps.appointments.models import Appointment, MedicalRecord
        from apps.notifications.models import Notification

        today = date.today()
        dr = self.doctors
        pt = self.patients

        def past(n):
            return self._workday(today - timedelta(days=n), forward=False)

        def future(n):
            return self._workday(today + timedelta(days=n), forward=True)

        appointments = [
            {
                'patient': pt[0], 'doctor': dr[0],
                'dt': self._make_dt(past(14), 10),
                'status': 'completed',
                'reason': 'Скарги на підвищену температуру, нежить та біль у горлі',
                'record': {
                    'diagnosis': 'ГРВІ, гострий ринофарингіт',
                    'treatment': (
                        'Постільний режим 5 днів, рясне тепле пиття, '
                        'парацетамол при температурі вище 38.5°C.'
                    ),
                    'doctor_notes': 'Пацієнт проінформований. Повторний огляд за потреби.',
                },
            },
            {
                'patient': pt[1], 'doctor': dr[3],
                'dt': self._make_dt(past(21), 14),
                'status': 'completed',
                'reason': 'Скарги на головний біль та підвищений артеріальний тиск',
                'record': {
                    'diagnosis': 'Гіпертонічна хвороба I ст.',
                    'treatment': (
                        'Амлодипін 5мг 1 раз на день, '
                        'обмеження солі до 5г на добу, контроль АТ щодня.'
                    ),
                    'doctor_notes': 'Призначено контрольний огляд через 1 місяць.',
                },
            },
            {
                'patient': pt[2], 'doctor': dr[7],
                'dt': self._make_dt(past(10), 11),
                'status': 'completed',
                'reason': 'Скарги на біль у зубі та підвищену чутливість до холодного',
                'record': {
                    'diagnosis': 'Карієс зуба 1.6',
                    'treatment': (
                        'Препарування та пломбування зуба композитним матеріалом, '
                        'гігієна порожнини рота.'
                    ),
                    'doctor_notes': 'Рекомендовано чищення зубів 2 рази на день.',
                },
            },
            {
                'patient': pt[3], 'doctor': dr[1],
                'dt': self._make_dt(past(7), 15),
                'status': 'completed',
                'reason': 'Скарги на погіршення зору вдалину та головний біль',
                'record': {
                    'diagnosis': 'Міопія слабкого ступеня обох очей',
                    'treatment': (
                        'Окуляри для постійного носіння -1.5 дптр, '
                        'повторний огляд через 6 місяців.'
                    ),
                    'doctor_notes': 'Рекомендовано зменшити час за екраном.',
                },
            },
            {
                'patient': pt[4], 'doctor': dr[2],
                'dt': self._make_dt(past(30), 10),
                'status': 'cancelled',
                'reason': 'Планова консультація невролога',
            },
            {
                'patient': pt[5], 'doctor': dr[5],
                'dt': self._make_dt(past(15), 13),
                'status': 'cancelled',
                'reason': 'Консультація перед плановою операцією',
            },
            {
                'patient': pt[6], 'doctor': dr[6],
                'dt': self._make_dt(past(20), 11),
                'status': 'cancelled',
                'reason': 'Психологічна консультація',
            },
            {
                'patient': pt[7], 'doctor': dr[9],
                'dt': self._make_dt(past(5), 14),
                'status': 'missed',
                'reason': 'Скарги на біль у суглобах колін',
            },
            {
                'patient': pt[8], 'doctor': dr[11],
                'dt': self._make_dt(past(3), 10),
                'status': 'missed',
                'reason': 'Контроль рівня цукру в крові',
            },
            {
                'patient': pt[9], 'doctor': dr[4],
                'dt': self._make_dt(past(8), 16),
                'status': 'missed',
                'reason': 'Повторний огляд педіатра',
            },
            {
                'patient': pt[0], 'doctor': dr[16],
                'dt': self._make_dt(future(3), 10),
                'status': 'planned',
                'reason': 'Планова консультація кардіолога',
            },
            {
                'patient': pt[1], 'doctor': dr[4],
                'dt': self._make_dt(future(5), 14),
                'status': 'planned',
                'reason': 'Профілактичний огляд педіатра',
            },
            {
                'patient': pt[2], 'doctor': dr[8],
                'dt': self._make_dt(future(7), 11),
                'status': 'planned',
                'reason': 'Консультація щодо вірусної інфекції',
            },
            {
                'patient': pt[4], 'doctor': dr[15],
                'dt': self._make_dt(future(9), 9),
                'status': 'planned',
                'reason': 'Планова консультація терапевта',
            },
            {
                'patient': pt[5], 'doctor': dr[19],
                'dt': self._make_dt(future(12), 15),
                'status': 'planned',
                'reason': 'Скарги на головний біль та запаморочення',
            },
        ]

        count = 0
        for item in appointments:
            appt, created = Appointment.objects.get_or_create(
                doctor=item['doctor'],
                date_time=item['dt'],
                defaults={
                    'patient': item['patient'],
                    'status': item['status'],
                    'reason': item['reason'],
                },
            )
            if not created:
                continue
            count += 1

            if item.get('record'):
                MedicalRecord.objects.get_or_create(
                    appointment=appt,
                    defaults=item['record'],
                )

            if item['status'] == 'planned':
                doc = item['doctor']
                Notification.objects.create(
                    user=item['patient'].user,
                    message=(
                        f'Ваш запис до лікаря {doc.get_full_name()} '
                        f'підтверджено на {item["dt"].strftime("%d.%m.%Y о %H:%M")}.'
                    ),
                    link=f'/appointments/{appt.id}/',
                )

        self.stdout.write(f'✓ Записи на прийом: {count} (4 completed, 3 cancelled, 3 missed, 5 planned)')

    def _print_accounts(self):
        W = 60
        self.stdout.write('\n' + '─' * W)
        self.stdout.write(self.style.SUCCESS('  ТЕСТОВІ АКАУНТИ'))
        self.stdout.write('─' * W)

        self.stdout.write('\n  Адмін:')
        self.stdout.write(f"    {'admin@mediculus.ua':<42} / Denysenko2026!")

        self.stdout.write('\n  Лікарі:')
        for d in self._DOCTORS_DATA:
            self.stdout.write(f"    {d['email']:<42} / {d['password']}")

        self.stdout.write('\n  Пацієнти:')
        for p in self._PATIENTS_DATA:
            self.stdout.write(f"    {p['email']:<42} / {p['password']}")

        self.stdout.write('─' * W + '\n')
