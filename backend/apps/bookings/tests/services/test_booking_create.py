import queue
import threading
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone

from apps.bookings.exceptions import (
    BookingConflict,
    BookingValidationError,
    CapacityExceeded,
    ResourceUnavailable,
)
from apps.bookings.models import Booking, BookingStatus, Resource, ResourceKind
from apps.bookings.services import booking_create


@pytest.mark.django_db(transaction=True)
def test_concurrent_requests_create_one_booking():
    resource = Resource.objects.create(
        kind=ResourceKind.UNIVERSITY_ROOM, name="101", capacity=30, is_active=True
    )
    users = [
        get_user_model().objects.create_user(username=f"client_{index}", password="password")
        for index in range(2)
    ]
    start_at = timezone.now().replace(microsecond=0) + timedelta(days=1)
    end_at = start_at + timedelta(hours=1)
    barrier = threading.Barrier(len(users))
    results = queue.Queue()

    def attempt(user):
        try:
            barrier.wait(timeout=10)
            booking_create(user=user, resource=resource, start_at=start_at, end_at=end_at, guests=1)
            results.put("created")
        except BookingConflict:
            results.put("conflict")
        except Exception as exc:
            results.put(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=attempt, args=(user,)) for user in users]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert not any(thread.is_alive() for thread in threads)
    outcomes = [results.get_nowait() for _ in range(results.qsize())]
    assert sorted(outcomes, key=str) == ["conflict", "created"]
    assert Booking.objects.filter(resource=resource, status=BookingStatus.CONFIRMED).count() == 1


@pytest.mark.django_db
def test_booking_create_returns_confirmed_booking(user, resource, times):
    start, end = times

    booking = booking_create(user=user, resource=resource, start_at=start, end_at=end, guests=2)

    assert booking.status == BookingStatus.CONFIRMED
    assert booking.effective_status == BookingStatus.CONFIRMED
    assert Booking.objects.get().user == user


@pytest.mark.django_db
def test_overlapping_booking_raises_conflict(user, other_user, resource, times):
    start, end = times
    booking_create(user=other_user, resource=resource, start_at=start, end_at=end, guests=1)

    with pytest.raises(BookingConflict):
        booking_create(
            user=user,
            resource=resource,
            start_at=start + timedelta(minutes=30),
            end_at=end + timedelta(minutes=30),
            guests=1,
        )
    assert Booking.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("case", ["past_start", "invalid_interval", "naive_start"])
def test_service_validates_time_without_serializer(user, resource, times, case):
    start, end = times
    if case == "past_start":
        start = timezone.now() - timedelta(hours=1)
    elif case == "invalid_interval":
        end = start
    elif case == "naive_start":
        start = timezone.make_naive(start)

    with pytest.raises(BookingValidationError):
        booking_create(user=user, resource=resource, start_at=start, end_at=end, guests=2)
    assert not Booking.objects.exists()


@pytest.mark.django_db
def test_service_rejects_zero_guests(user, resource, times):
    start, end = times

    with pytest.raises(ValidationError):
        booking_create(user=user, resource=resource, start_at=start, end_at=end, guests=0)
    assert not Booking.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "attribute, value, exception_class",
    [
        ("is_active", False, ResourceUnavailable),
        ("capacity", 1, CapacityExceeded),
    ],
)
def test_service_rechecks_resource_state(user, resource, times, attribute, value, exception_class):
    setattr(resource, attribute, value)
    resource.save(update_fields=[attribute])
    start, end = times

    with pytest.raises(exception_class):
        booking_create(user=user, resource=resource, start_at=start, end_at=end, guests=2)
    assert not Booking.objects.exists()


@pytest.mark.django_db
def test_deleted_resource_is_unavailable(user, resource, times):
    start, end = times
    Resource.objects.filter(pk=resource.pk).delete()

    with pytest.raises(ResourceUnavailable):
        booking_create(user=user, resource=resource, start_at=start, end_at=end, guests=1)
