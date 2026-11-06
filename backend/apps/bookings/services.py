from datetime import datetime

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.exceptions import (
    BookingAlreadyCancelled,
    BookingCompleted,
    BookingConflict,
    BookingNotFound,
    BookingValidationError,
    CapacityExceeded,
    ResourceUnavailable,
)
from apps.bookings.models import Booking, BookingStatus, Resource
from apps.bookings.selectors import booking_get


def _is_overlap_constraint_error(exc: IntegrityError) -> bool:
    """Функция, определяющая, что база отклонила запись из-за пересечения броней"""
    cause = exc.__cause__
    diag = getattr(cause, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    return constraint_name == "booking_no_overlap" or "booking_no_overlap" in str(exc)


def _booking_full_clean(booking: Booking) -> None:
    """Функция, проверяющая бронь правилами модели и превращающая пересечение в конфликт"""
    try:
        booking.full_clean()
    except ValidationError as exc:
        overlap = next(c for c in Booking._meta.constraints if c.name == "booking_no_overlap")
        overlap_message = overlap.get_violation_error_message()
        errors = getattr(exc, "error_dict", {}).get(NON_FIELD_ERRORS, [])
        if any(error.message == overlap_message for error in errors):
            raise BookingConflict() from exc
        raise


def booking_create(
    *, user: User, resource: Resource, start_at: datetime, end_at: datetime, guests: int
) -> Booking:
    """Функция, создающая подтвержденную бронь после проверки времени, ресурса и пересечений"""
    if timezone.is_naive(start_at) or timezone.is_naive(end_at):
        raise BookingValidationError("Dates must include a timezone.")

    if start_at >= end_at:
        raise BookingValidationError("End time must be after start time.")

    if start_at <= timezone.now():
        raise BookingValidationError("Start time must be in the future.")

    try:
        with transaction.atomic():
            locked_resource = Resource.objects.select_for_update().filter(pk=resource.pk).first()
            if locked_resource is None or not locked_resource.is_active:
                raise ResourceUnavailable()

            if guests > locked_resource.capacity:
                raise CapacityExceeded()

            booking = Booking(
                resource=locked_resource,
                user=user,
                start_at=start_at,
                end_at=end_at,
                guests=guests,
                status=BookingStatus.CONFIRMED,
            )
            _booking_full_clean(booking)
            booking.save()
    except IntegrityError as exc:
        if _is_overlap_constraint_error(exc):
            raise BookingConflict() from exc
        raise

    return booking_get(user=user, booking_id=booking.pk)


def booking_cancel(*, user: User, booking_id: int) -> Booking:
    """Функция, отменяющая действующую бронь пользователя и освобождающая ее время"""
    with transaction.atomic():
        booking = Booking.objects.select_for_update().filter(pk=booking_id, user=user).first()
        if booking is None:
            raise BookingNotFound()

        if booking.status == BookingStatus.CANCELLED:
            raise BookingAlreadyCancelled()

        if booking.status == BookingStatus.COMPLETED or booking.end_at <= timezone.now():
            raise BookingCompleted()

        booking.status = BookingStatus.CANCELLED
        booking.full_clean()
        booking.save(update_fields=["status", "updated_at"])

    return booking_get(user=user, booking_id=booking.pk)


def resource_set_active(*, resource: Resource, is_active: bool) -> Resource:
    """Функция, включающая или выключающая ресурс для новых бронирований"""
    resource.is_active = is_active
    resource.full_clean()
    resource.save(update_fields=["is_active", "updated_at"])
    return resource
