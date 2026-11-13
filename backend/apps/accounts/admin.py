from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import User


@admin.register(User)
class BookPlanUserAdmin(UserAdmin):
    """Класс, настраивающий раздел пользователей в админке Django"""

    fieldsets = (*(UserAdmin.fieldsets or ()), ("Роль", {"fields": ("role",)}))
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "role")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups", "role")
