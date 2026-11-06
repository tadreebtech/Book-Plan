from datetime import datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.models import Resource, ResourceKind


@pytest.fixture
def user() -> User:
    return get_user_model().objects.create_user(username="booking_alice", password="test-pass-123")


@pytest.fixture
def other_user() -> User:
    return get_user_model().objects.create_user(username="booking_bob", password="test-pass-456")


@pytest.fixture
def resource() -> Resource:
    return Resource.objects.create(
        kind=ResourceKind.UNIVERSITY_ROOM,
        name="Аудитория 101",
        capacity=4,
        is_active=True,
    )


@pytest.fixture
def times() -> tuple[datetime, datetime]:
    start = timezone.now().replace(microsecond=0) + timedelta(days=2)
    return start, start + timedelta(hours=1)
