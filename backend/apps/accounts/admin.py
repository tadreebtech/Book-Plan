from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.forms import ModelForm
from django.http import HttpRequest
from rest_framework.exceptions import APIException

from apps.accounts.models import AuditLog, User
from apps.accounts.services import user_role_change


@admin.register(User)
class BookPlanUserAdmin(UserAdmin):
    """Класс, настраивающий раздел пользователей в админке Django"""

    fieldsets = (*(UserAdmin.fieldsets or ()), ("Роль", {"fields": ("role",)}))
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "role")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups", "role")

    def save_model(self, request: HttpRequest, obj: User, form: ModelForm, change: bool) -> None:
        """Метод, сохраняющий пользователя и меняющий его роль через сервис с записью в аудит"""

        if not (change and "role" in form.changed_data):
            super().save_model(request, obj, form, change)
            return

        new_role = obj.role
        obj.role = form.initial["role"]
        super().save_model(request, obj, form, change)
        try:
            user_role_change(actor=request.user, user_id=obj.pk, role=new_role)
        except APIException as exc:
            self.message_user(request, f"Роль не изменена: {exc.detail}", messages.ERROR)
        else:
            obj.role = new_role


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Класс, показывающий журнал действий над пользователями в админке"""

    list_display = ("created_at", "actor", "action", "target", "old_value", "new_value")
    list_filter = ("action", "created_at")
    search_fields = ("actor__username", "target__username")
    readonly_fields = (
        "created_at",
        "updated_at",
        "actor",
        "action",
        "target",
        "old_value",
        "new_value",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Метод, запрещающий ручное создание записей аудита"""

        return False

    def has_change_permission(self, request: HttpRequest, obj: AuditLog | None = None) -> bool:
        """Метод, разрешающий просмотр без изменения записей аудита"""

        return False

    def has_delete_permission(self, request: HttpRequest, obj: AuditLog | None = None) -> bool:
        """Метод, запрещающий удаление записей аудита"""

        return False
