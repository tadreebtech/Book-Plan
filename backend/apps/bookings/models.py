from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeBoundary, RangeOperators
from django.db import models
from django.db.models import F, Q

from apps.accounts.models import Role
from apps.common.models import BaseModel


class ResourceKind(models.TextChoices):
    """Класс, перечисляющий виды ресурсов, которые можно забронировать"""

    UNIVERSITY_ROOM = "UNIVERSITY_ROOM", "Помещение университета"
    RESTAURANT_TABLE = "RESTAURANT_TABLE", "Столик ресторана"
    HOTEL_ROOM = "HOTEL_ROOM", "Номер отеля"


class BookingStatus(models.TextChoices):
    """Класс, перечисляющий состояния брони: действует, отменена, завершена"""

    CONFIRMED = "CONFIRMED", "Подтверждено"
    CANCELLED = "CANCELLED", "Отменено"
    COMPLETED = "COMPLETED", "Завершено"


class TsTzRange(models.Func):
    """Класс, склеивающий начало и конец брони в один отрезок времени PostgreSQL"""

    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class Resource(BaseModel):
    """Класс, описывающий ресурс для бронирования: аудиторию, столик или номер"""

    kind = models.CharField(max_length=32, choices=ResourceKind.choices)
    name = models.CharField(max_length=255)
    capacity = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_resources",
        limit_choices_to={"role": Role.MANAGER},
    )

    class Meta:
        """Класс, задающий правила таблицы ресурсов, которые проверяет сама база данных"""

        constraints = [
            models.CheckConstraint(
                condition=Q(kind__in=ResourceKind.values), name="resource_kind_valid"
            ),
            models.CheckConstraint(condition=Q(capacity__gte=1), name="resource_capacity_gte_1"),
        ]

    def __str__(self) -> str:
        return self.name


class Booking(BaseModel):
    """Класс, описывающий бронь ресурса клиентом на отрезок времени"""

    resource = models.ForeignKey(Resource, on_delete=models.PROTECT, related_name="bookings")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings"
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    guests = models.PositiveIntegerField()
    status = models.CharField(
        max_length=16, choices=BookingStatus.choices, default=BookingStatus.CONFIRMED
    )

    class Meta:
        """Класс, задающий правила таблицы броней, которые проверяет сама база данных"""

        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=BookingStatus.values), name="booking_status_valid"
            ),
            models.CheckConstraint(
                condition=Q(end_at__gt=F("start_at")), name="booking_end_after_start"
            ),
            models.CheckConstraint(condition=Q(guests__gte=1), name="booking_guests_gte_1"),
            ExclusionConstraint(
                name="booking_no_overlap",
                expressions=[
                    ("resource", RangeOperators.EQUAL),
                    (TsTzRange("start_at", "end_at", RangeBoundary()), RangeOperators.OVERLAPS),
                ],
                condition=~Q(status=BookingStatus.CANCELLED),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.resource} {self.start_at:%Y-%m-%d %H:%M}"
