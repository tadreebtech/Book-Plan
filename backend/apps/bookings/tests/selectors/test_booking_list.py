from datetime import timedelta

import pytest
from django.utils import timezone

from apps.bookings.models import Booking, BookingStatus
from apps.bookings.selectors import booking_list

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "days, stored_status, expected_status",
    [
        (1, BookingStatus.CONFIRMED, BookingStatus.CONFIRMED),
        (-1, BookingStatus.CONFIRMED, BookingStatus.COMPLETED),
        (-1, BookingStatus.CANCELLED, BookingStatus.CANCELLED),
        (1, BookingStatus.COMPLETED, BookingStatus.COMPLETED),
    ],
)
def test_booking_list_computes_effective_status(
    user, resource, days, stored_status, expected_status
):
    start = timezone.now() + timedelta(days=days)
    Booking.objects.create(
        resource=resource,
        user=user,
        start_at=start,
        end_at=start + timedelta(hours=1),
        guests=1,
        status=stored_status,
    )

    booking = booking_list(user=user).get()

    assert booking.effective_status == expected_status
    assert booking.status == stored_status


def test_booking_list_returns_only_own_bookings_latest_first(user, other_user, resource, times):
    start, end = times
    early = Booking.objects.create(
        resource=resource, user=user, start_at=start, end_at=end, guests=1
    )
    late = Booking.objects.create(
        resource=resource,
        user=user,
        start_at=start + timedelta(hours=2),
        end_at=end + timedelta(hours=2),
        guests=1,
    )
    Booking.objects.create(
        resource=resource,
        user=other_user,
        start_at=start + timedelta(hours=4),
        end_at=end + timedelta(hours=4),
        guests=1,
    )

    assert list(booking_list(user=user)) == [late, early]
