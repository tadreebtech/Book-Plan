from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import PermissionDenied
from django.forms import ModelForm
from django.http import HttpRequest
from rest_framework.exceptions import APIException

from apps.accounts.models import AuditLog, Role, User
from apps.accounts.services import user_role_change


@admin.register(User)
class BookPlanUserAdmin(UserAdmin):
    """Класс, настраивающий раздел пользователей в админке Django"""

    fieldsets = (*(UserAdmin.fieldsets or ()), ("Роль", {"fields": ("role",)}))
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "role")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups", "role")

    def get_readonly_fields(self, request: HttpRequest, obj: User | None = None) -> list[str]:
        """Метод, запрещающий править роль не-администратору и администратору у самого себя"""

        readonly_fields = list(super().get_readonly_fields(request, obj))
        user = request.user
        if obj and (user.role != Role.ADMIN or not user.is_active or obj.pk == user.pk):
            readonly_fields.append("role")
        return readonly_fields

    def save_model(self, request: HttpRequest, obj: User, form: ModelForm, change: bool) -> None:
        """Метод, сохраняющий пользователя и меняющий его роль через сервис с записью в аудит"""

        if change and "role" in form.changed_data:
            try:
                user_role_change(actor=request.user, user_id=obj.pk, role=obj.role)
            except APIException as exc:
                raise PermissionDenied(str(exc.detail)) from exc
        super().save_model(request, obj, form, change)


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
