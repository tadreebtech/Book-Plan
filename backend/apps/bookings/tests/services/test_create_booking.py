import queue
import threading
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone

from apps.bookings.exceptions import BookingConflict
from apps.bookings.models import Booking, BookingStatus, Resource, ResourceKind
from apps.bookings.services import create_booking


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
            create_booking(user=user, resource=resource, start_at=start_at, end_at=end_at, guests=1)
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
