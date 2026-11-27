from collections.abc import Callable

from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Role, User

from .models import Booking, BookingStatus, Resource, ResourceActivationLog
from .services import resource_activate, resource_deactivate


def _is_platform_admin(user: User) -> bool:
    """Функция, проверяющая, что пользователь является активным администратором платформы"""

    return user.is_active and getattr(user, "role", None) == Role.ADMIN


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    """Класс, показывающий ресурсы в админке с действиями активации и деактивации"""

    list_display = ("id", "name", "kind", "capacity", "is_active", "upcoming_bookings")
    list_filter = ("kind", "is_active")
    actions = ("activate_resources", "deactivate_resources")
    confirmation_template = "admin/bookings/resource/activation_confirmation.html"

    def get_queryset(self, request: HttpRequest) -> QuerySet[Resource]:
        """Метод, добавляющий к ресурсам число действующих будущих броней"""

        return (
            super()
            .get_queryset(request)
            .annotate(
                upcoming_bookings_count=Count(
                    "bookings",
                    filter=Q(
                        bookings__status=BookingStatus.CONFIRMED,
                        bookings__end_at__gt=timezone.now(),
                    ),
                )
            )
        )

    @admin.display(description="Будущие брони", ordering="upcoming_bookings_count")
    def upcoming_bookings(self, obj: Resource) -> int:
        """Метод, возвращающий число действующих будущих броней ресурса"""

        return obj.upcoming_bookings_count

    def get_actions(self, request: HttpRequest) -> dict:
        """Метод, оставляющий действия активации только администратору платформы"""

        actions = super().get_actions(request)
        if not _is_platform_admin(request.user):
            actions.pop("activate_resources", None)
            actions.pop("deactivate_resources", None)
        return actions

    @admin.action(description="Активировать выбранные ресурсы")
    def activate_resources(
        self, request: HttpRequest, queryset: QuerySet[Resource]
    ) -> HttpResponse | None:
        """Метод, активирующий выбранные ресурсы после подтверждения"""

        return self._change_activity(
            request,
            queryset,
            action="activate_resources",
            is_active=True,
            service=resource_activate,
        )

    @admin.action(description="Деактивировать выбранные ресурсы")
    def deactivate_resources(
        self, request: HttpRequest, queryset: QuerySet[Resource]
    ) -> HttpResponse | None:
        """Метод, деактивирующий выбранные ресурсы после подтверждения"""

        return self._change_activity(
            request,
            queryset,
            action="deactivate_resources",
            is_active=False,
            service=resource_deactivate,
        )

    def _change_activity(
        self,
        request: HttpRequest,
        queryset: QuerySet[Resource],
        *,
        action: str,
        is_active: bool,
        service: Callable[..., Resource],
    ) -> HttpResponse | None:
        """Метод, показывающий страницу подтверждения и меняющий активность ресурсов"""

        if not _is_platform_admin(request.user):
            self.message_user(request, "Действие доступно только администратору.", messages.ERROR)
            return None

        resources = list(queryset.order_by("pk"))
        if request.POST.get("post") == "yes":
            changed = 0
            for resource in resources:
                if resource.is_active == is_active:
                    continue
                try:
                    service(actor=request.user, resource_id=resource.pk)
                except PermissionDenied:
                    self.message_user(
                        request, "Действие доступно только администратору.", messages.ERROR
                    )
                    return None
                changed += 1
            verb = "активировано" if is_active else "деактивировано"
            self.message_user(request, f"Ресурсов {verb}: {changed}.", messages.SUCCESS)
            return None

        to_change = [resource for resource in resources if resource.is_active != is_active]
        context = {
            **self.admin_site.each_context(request),
            "title": "Подтвердите активацию" if is_active else "Подтвердите деактивацию",
            "opts": self.model._meta,
            "action": action,
            "is_active": is_active,
            "resources": to_change,
            "unchanged": [resource for resource in resources if resource.is_active == is_active],
            "bookings_total": sum(r.upcoming_bookings_count for r in to_change),
            "queryset": queryset,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        }
        return TemplateResponse(request, self.confirmation_template, context)


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
