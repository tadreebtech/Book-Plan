from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.models import Booking, BookingStatus, Resource, ResourceKind


@pytest.fixture
def resource():
    return Resource.objects.create(kind=ResourceKind.UNIVERSITY_ROOM, name="101", capacity=30)


@pytest.fixture
def user():
    return User.objects.create_user(username="client", password="password")


def book(resource, user, start, hours=1, status=BookingStatus.CONFIRMED):
    return Booking.objects.create(
        resource=resource,
        user=user,
        start_at=start,
        end_at=start + timedelta(hours=hours),
        guests=1,
        status=status,
    )


@pytest.mark.django_db
def test_overlapping_bookings_are_rejected(resource, user):
    start = timezone.now()
    book(resource, user, start, hours=2)

    with pytest.raises(IntegrityError):
        book(resource, user, start + timedelta(hours=1))


@pytest.mark.django_db
def test_adjacent_bookings_are_allowed(resource, user):
    start = timezone.now()
    book(resource, user, start)
    book(resource, user, start + timedelta(hours=1))

    assert Booking.objects.count() == 2


@pytest.mark.django_db
def test_cancelled_booking_does_not_block_slot(resource, user):
    start = timezone.now()
    book(resource, user, start, status=BookingStatus.CANCELLED)
    book(resource, user, start)

    assert Booking.objects.count() == 2
