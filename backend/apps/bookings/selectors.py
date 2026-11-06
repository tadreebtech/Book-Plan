from django.db import models
from django.db.models import Case, Q, QuerySet, Value, When
from django.db.models.functions import Now

from apps.accounts.models import User
from apps.bookings.exceptions import BookingNotFound
from apps.bookings.models import Booking, BookingStatus


def _booking_queryset() -> QuerySet[Booking]:
    """Функция, возвращающая все брони от поздних к ранним с фактическим статусом effective_status"""
    effective_status = Case(
        When(status=BookingStatus.CANCELLED, then=Value(BookingStatus.CANCELLED)),
        When(
            Q(status=BookingStatus.COMPLETED) | Q(end_at__lte=Now()),
            then=Value(BookingStatus.COMPLETED),
        ),
        default=Value(BookingStatus.CONFIRMED),
        output_field=models.CharField(),
    )
    return (
        Booking.objects.select_related("resource", "user")
        .annotate(effective_status=effective_status)
        .order_by("-start_at", "-pk")
    )


def booking_list_all() -> QuerySet[Booking]:
    """Функция, возвращающая брони всех пользователей платформы с фактическим статусом"""
    return _booking_queryset()


def booking_list(*, user: User) -> QuerySet[Booking]:
    """Функция, возвращающая брони одного пользователя от поздних к ранним с фактическим статусом"""
    return _booking_queryset().filter(user=user)


def booking_get(*, user: User, booking_id: int) -> Booking:
    """Функция, возвращающая одну бронь пользователя с фактическим статусом или ошибку NOT_FOUND"""
    booking = booking_list(user=user).filter(pk=booking_id).first()
    if booking is None:
        raise BookingNotFound()
    return booking
