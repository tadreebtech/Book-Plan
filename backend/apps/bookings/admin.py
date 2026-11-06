from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.bookings.models import Booking, BookingStatus, Resource
from apps.bookings.selectors import booking_list_all
from apps.bookings.services import booking_cancel, resource_set_active
from apps.common.exceptions import ApplicationError


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    """Класс, настраивающий раздел ресурсов в админке Django"""

    list_display = ("id", "name", "kind", "capacity", "manager", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("name",)
    actions = ("activate_resources", "deactivate_resources")

    @admin.action(description="Активировать выбранные ресурсы", permissions=["change"])
    def activate_resources(self, request: HttpRequest, queryset: QuerySet[Resource]) -> None:
        """Метод, открывающий выбранные ресурсы для новых бронирований"""
        self._set_active(request, queryset, is_active=True)

    @admin.action(description="Деактивировать выбранные ресурсы", permissions=["change"])
    def deactivate_resources(self, request: HttpRequest, queryset: QuerySet[Resource]) -> None:
        """Метод, закрывающий выбранные ресурсы для новых бронирований"""
        self._set_active(request, queryset, is_active=False)

    def _set_active(
        self, request: HttpRequest, queryset: QuerySet[Resource], *, is_active: bool
    ) -> None:
        """Метод, меняющий активность каждого ресурса через service и сообщающий итог"""
        for resource in queryset:
            resource_set_active(resource=resource, is_active=is_active)
        state = "активировано" if is_active else "деактивировано"
        self.message_user(request, f"Ресурсов {state}: {queryset.count()}", messages.SUCCESS)


class EffectiveStatusFilter(admin.SimpleListFilter):
    """Класс, фильтрующий брони в админке по фактическому статусу с учетом времени окончания"""

    title = "статус"
    parameter_name = "effective_status"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list:
        """Метод, перечисляющий статусы, по которым можно отфильтровать список"""
        return BookingStatus.choices

    def queryset(self, request: HttpRequest, queryset: QuerySet[Booking]) -> QuerySet[Booking]:
        """Метод, оставляющий в списке брони с выбранным фактическим статусом"""
        if self.value() is None:
            return queryset
        return queryset.filter(effective_status=self.value())


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Класс, показывающий брони всех пользователей в админке"""

    list_display = (
        "id",
        "resource",
        "user",
        "start_at",
        "end_at",
        "guests",
        "effective_status_display",
    )
    list_filter = (EffectiveStatusFilter, "resource__kind")
    search_fields = ("resource__name", "user__username")
    fields = (
        "resource",
        "user",
        "start_at",
        "end_at",
        "guests",
        "status",
        "effective_status_display",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("effective_status_display", "created_at", "updated_at")
    actions = ("cancel_bookings",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Booking]:
        """Метод, берущий брони из selector, чтобы у каждой был фактический статус"""
        return booking_list_all()

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Метод, запрещающий создавать брони в админке в обход проверок service"""
        return False

    def has_change_permission(self, request: HttpRequest, obj: Booking | None = None) -> bool:
        """Метод, запрещающий редактировать поля брони в админке"""
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Booking | None = None) -> bool:
        """Метод, запрещающий удалять брони, чтобы история бронирований сохранялась"""
        return False

    def has_cancel_permission(self, request: HttpRequest) -> bool:
        """Метод, разрешающий отмену броней только пользователям с правом изменять брони"""
        return request.user.has_perm("bookings.change_booking")

    @admin.display(description="Статус", ordering="effective_status")
    def effective_status_display(self, obj: Booking) -> str:
        """Метод, показывающий фактический статус брони по-русски"""
        return BookingStatus(obj.effective_status).label

    @admin.action(description="Отменить выбранные брони", permissions=["cancel"])
    def cancel_bookings(self, request: HttpRequest, queryset: QuerySet[Booking]) -> None:
        """Метод, отменяющий выбранные брони через service и сообщающий о каждой ошибке"""
        cancelled_count = 0
        for booking in queryset:
            try:
                booking_cancel(user=booking.user, booking_id=booking.pk)
            except ApplicationError as exc:
                self.message_user(request, f"Бронь {booking.pk}: {exc.message}", messages.ERROR)
            else:
                cancelled_count += 1
        if cancelled_count:
            self.message_user(request, f"Отменено броней: {cancelled_count}", messages.SUCCESS)
