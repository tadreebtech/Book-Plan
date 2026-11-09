from datetime import datetime

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework.exceptions import NotFound

from apps.accounts.models import User
from apps.bookings.exceptions import BookingConflict, BookingValidationError, ResourceUnavailable
from apps.bookings.models import Booking, BookingStatus, Resource


def _is_overlap_constraint_error(exc: IntegrityError) -> bool:
    cause = exc.__cause__
    diag = getattr(cause, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    return constraint_name == "booking_no_overlap" or "booking_no_overlap" in str(exc)


def create_booking(
    *, user: User, resource: Resource, start_at: datetime, end_at: datetime, guests: int
) -> Booking:
    if timezone.is_naive(start_at) or timezone.is_naive(end_at):
        raise BookingValidationError("Dates must include a timezone.")

    if start_at >= end_at:
        raise BookingValidationError("End time must be after start time.")

    if start_at <= timezone.now():
        raise BookingValidationError("Start time must be in the future.")

    if guests < 1:
        raise BookingValidationError("Guests must be at least 1.")

    try:
        with transaction.atomic():
            try:
                locked_resource = Resource.objects.select_for_update().get(pk=resource.pk)
            except Resource.DoesNotExist as exc:
                raise NotFound("Resource not found.") from exc

            if not locked_resource.is_active:
                raise ResourceUnavailable("Resource is unavailable.")

            if guests > locked_resource.capacity:
                raise BookingValidationError(
                    "Guests exceed resource capacity.",
                    code="CAPACITY_EXCEEDED",
                )

            overlap_exists = (
                Booking.objects.filter(
                    resource=locked_resource,
                    start_at__lt=end_at,
                    end_at__gt=start_at,
                )
                .exclude(status=BookingStatus.CANCELLED)
                .exists()
            )

            if overlap_exists:
                raise BookingConflict("Resource is already booked for this time slot.")

            return Booking.objects.create(
                resource=locked_resource,
                user=user,
                start_at=start_at,
                end_at=end_at,
                guests=guests,
                status=BookingStatus.CONFIRMED,
            )
    except IntegrityError as exc:
        if _is_overlap_constraint_error(exc):
            raise BookingConflict("Resource is already booked for this time slot.") from exc
        raise


def list_user_bookings(*, user: User) -> QuerySet[Booking]:
    return Booking.objects.filter(user=user).select_related("resource").order_by("-start_at", "-pk")


def cancel_booking(*, user: User, booking_id: int) -> Booking:
    with transaction.atomic():
        try:
            booking = (
                Booking.objects.select_for_update()
                .select_related("resource")
                .get(pk=booking_id, user=user)
            )
        except Booking.DoesNotExist as exc:
            raise NotFound("Booking not found.") from exc

        if booking.status == BookingStatus.CANCELLED:
            raise BookingConflict("Booking is already cancelled.", code="ALREADY_CANCELLED")

        if booking.status == BookingStatus.COMPLETED or booking.end_at <= timezone.now():
            raise BookingConflict(
                "Completed bookings cannot be cancelled.",
                code="BOOKING_COMPLETED",
            )

        booking.status = BookingStatus.CANCELLED
        booking.save(update_fields=["status", "updated_at"])
        return booking
