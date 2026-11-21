from django.contrib import admin
from django.http import HttpRequest

from .models import Booking, Resource, ResourceActivationLog


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "kind", "capacity", "is_active")
    list_filter = ("kind", "is_active")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "resource", "user", "start_at", "end_at", "status")
    list_filter = ("status",)


@admin.register(ResourceActivationLog)
class ResourceActivationLogAdmin(admin.ModelAdmin):
    """Класс, показывающий журнал активации и деактивации ресурсов в админке"""

    list_display = ("created_at", "actor", "action", "resource_id")
    list_filter = ("action", "created_at")
    search_fields = ("actor__username", "resource_id")
    readonly_fields = ("created_at", "updated_at", "actor", "action", "resource_id")

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Метод, запрещающий ручное создание записей журнала"""

        return False

    def has_change_permission(
        self, request: HttpRequest, obj: ResourceActivationLog | None = None
    ) -> bool:
        """Метод, разрешающий просмотр без изменения записей журнала"""

        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: ResourceActivationLog | None = None
    ) -> bool:
        """Метод, запрещающий удаление записей журнала"""

        return False
