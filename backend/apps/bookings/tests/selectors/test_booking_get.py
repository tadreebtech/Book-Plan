import pytest

from apps.bookings.exceptions import BookingNotFound
from apps.bookings.models import Booking, BookingStatus
from apps.bookings.selectors import booking_get

pytestmark = pytest.mark.django_db


def test_booking_get_returns_own_booking_with_effective_status(user, resource, times):
    start, end = times
    booking = Booking.objects.create(
        resource=resource, user=user, start_at=start, end_at=end, guests=1
    )

    found = booking_get(user=user, booking_id=booking.pk)

    assert found == booking
    assert found.effective_status == BookingStatus.CONFIRMED


def test_booking_get_hides_other_users_booking(user, other_user, resource, times):
    start, end = times
    foreign = Booking.objects.create(
        resource=resource, user=other_user, start_at=start, end_at=end, guests=1
    )

    with pytest.raises(BookingNotFound):
        booking_get(user=user, booking_id=foreign.pk)
