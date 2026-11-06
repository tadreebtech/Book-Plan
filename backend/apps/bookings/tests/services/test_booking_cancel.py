from datetime import timedelta

import pytest
from django.utils import timezone

from apps.bookings.exceptions import BookingAlreadyCancelled, BookingCompleted, BookingNotFound
from apps.bookings.models import Booking, BookingStatus
from apps.bookings.services import booking_cancel

pytestmark = pytest.mark.django_db


def test_booking_cancel_marks_booking_cancelled(user, resource, times):
    start, end = times
    booking = Booking.objects.create(
        resource=resource, user=user, start_at=start, end_at=end, guests=1
    )

    cancelled = booking_cancel(user=user, booking_id=booking.pk)

    assert cancelled.effective_status == BookingStatus.CANCELLED
    booking.refresh_from_db()
    assert booking.status == BookingStatus.CANCELLED


def test_second_cancel_is_rejected(user, resource, times):
    start, end = times
    booking = Booking.objects.create(
        resource=resource,
        user=user,
        start_at=start,
        end_at=end,
        guests=1,
        status=BookingStatus.CANCELLED,
    )

    with pytest.raises(BookingAlreadyCancelled):
        booking_cancel(user=user, booking_id=booking.pk)


def test_cannot_cancel_other_users_booking(user, other_user, resource, times):
    start, end = times
    foreign = Booking.objects.create(
        resource=resource, user=other_user, start_at=start, end_at=end, guests=1
    )

    with pytest.raises(BookingNotFound):
        booking_cancel(user=user, booking_id=foreign.pk)
    foreign.refresh_from_db()
    assert foreign.status == BookingStatus.CONFIRMED


def test_service_rejects_cancellation_of_elapsed_booking(user, resource):
    end = timezone.now() - timedelta(hours=1)
    booking = Booking.objects.create(
        user=user,
        resource=resource,
        start_at=end - timedelta(hours=1),
        end_at=end,
        guests=1,
    )

    with pytest.raises(BookingCompleted):
        booking_cancel(user=user, booking_id=booking.pk)
    booking.refresh_from_db()
    assert booking.status == BookingStatus.CONFIRMED
