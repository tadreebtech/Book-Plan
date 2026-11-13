from datetime import date, datetime, time, timedelta

from django.db.models import QuerySet
from django.utils import timezone

from apps.bookings.models import Booking


def _day_start(*, day: date) -> datetime:
    """Функция, возвращающая начало указанного дня в часовом поясе проекта"""

    return timezone.make_aware(datetime.combine(day, time.min))


def booking_list(
    *,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    provider_id: int | None = None,
    client_id: int | None = None,
    ordering: str = "-created_at",
) -> QuerySet[Booking]:
    """Функция, выбирающая брони платформы по фильтрам и порядку сортировки

    Даты задают отрезок дней включительно: в выборку попадают брони, период которых
    хотя бы частично приходится на эти дни
    """

    bookings = Booking.objects.select_related("resource", "resource__manager", "user")

    if status is not None:
        bookings = bookings.filter(status=status)

    if date_from is not None:
        bookings = bookings.filter(end_at__gt=_day_start(day=date_from))

    if date_to is not None:
        bookings = bookings.filter(start_at__lt=_day_start(day=date_to + timedelta(days=1)))

    if category is not None:
        bookings = bookings.filter(resource__kind=category)

    if provider_id is not None:
        bookings = bookings.filter(resource__manager_id=provider_id)

    if client_id is not None:
        bookings = bookings.filter(user_id=client_id)

    secondary_ordering = "-id" if ordering.startswith("-") else "id"
    return bookings.order_by(ordering, secondary_ordering)


def booking_get(*, booking_id: int) -> Booking | None:
    """Функция, получающая бронь с клиентом, ресурсом и менеджером ресурса при её наличии"""

    return (
        Booking.objects.select_related("resource", "resource__manager", "user")
        .filter(pk=booking_id)
        .first()
    )
