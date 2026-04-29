from django.contrib import admin
from django.contrib.auth.models import Group

# Кастомний заголовок адмін панелі
admin.site.site_header = 'Mediculus — Адміністрування'
admin.site.site_title = 'Mediculus Admin'
admin.site.index_title = 'Панель управління лікарнею'

# Приховати зайві розділи
admin.site.unregister(Group)

# Приховати Чорний список токенів (token_blacklist)
try:
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
    admin.site.unregister(OutstandingToken)
    admin.site.unregister(BlacklistedToken)
except Exception:
    pass
