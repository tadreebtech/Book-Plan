from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.models import Booking, BookingStatus, Resource, ResourceKind

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return get_user_model().objects.create_user(username="booking_alice", password="test-pass-123")


@pytest.fixture
def other_user():
    return get_user_model().objects.create_user(username="booking_bob", password="test-pass-456")


@pytest.fixture
def resource():
    return Resource.objects.create(
        kind=ResourceKind.UNIVERSITY_ROOM,
        name="Аудитория 101",
        capacity=4,
        is_active=True,
    )


@pytest.fixture
def api(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def times():
    start = timezone.now() + timedelta(days=2)
    start = start.replace(microsecond=0)
    return start, start + timedelta(hours=1)


def payload(resource, times, **changes):
    start, end = times
    data = {
        "resource": resource.pk,
        "start_at": start.isoformat(),
        "end_at": end.isoformat(),
        "guests": 2,
    }
    data.update(changes)
    return data


def test_create_booking(api, user, resource, times):
    response = api.post("/api/v1/bookings/", payload(resource, times), format="json")

    assert response.status_code == 201, response.data
    booking = Booking.objects.get(pk=response.data["id"])
    assert booking.user_id == user.pk
    assert booking.resource_id == resource.pk
    assert booking.status == BookingStatus.CONFIRMED
    assert response.data["status"] == BookingStatus.CONFIRMED
    assert response.data["resource_name"] == "Аудитория 101"


def test_requires_authentication(resource, times):
    response = APIClient().get("/api/v1/bookings/")
    assert response.status_code in (401, 403)
    assert response.data["error"]["code"]

    response = APIClient().post("/api/v1/bookings/", payload(resource, times), format="json")
    assert response.status_code in (401, 403)
    assert "error" in response.data


def test_list_and_details_are_only_for_owner(api, user, other_user, resource, times):
    start, end = times
    own = Booking.objects.create(resource=resource, user=user, start_at=start, end_at=end, guests=2)
    foreign = Booking.objects.create(
        resource=resource,
        user=other_user,
        start_at=start + timedelta(hours=2),
        end_at=end + timedelta(hours=2),
        guests=1,
    )

    listed = api.get("/api/v1/bookings/")
    assert listed.status_code == 200
    assert [row["id"] for row in listed.data] == [own.pk]
    assert api.get(f"/api/v1/bookings/{own.pk}/").status_code == 200

    denied = api.get(f"/api/v1/bookings/{foreign.pk}/")
    assert denied.status_code == 404
    assert denied.data["error"]["code"] == "not_found"


def test_overlap_rejected_but_adjacent_time_allowed(api, resource, times):
    start, end = times
    assert api.post("/api/v1/bookings/", payload(resource, times), format="json").status_code == 201

    conflicting = api.post(
        "/api/v1/bookings/",
        payload(
            resource,
            times,
            start_at=(start + timedelta(minutes=30)).isoformat(),
            end_at=(end + timedelta(minutes=30)).isoformat(),
        ),
        format="json",
    )
    assert conflicting.status_code == 409
    assert conflicting.data["error"]["code"] == "booking_conflict"

    adjacent = api.post(
        "/api/v1/bookings/",
        payload(
            resource, times, start_at=end.isoformat(), end_at=(end + timedelta(hours=1)).isoformat()
        ),
        format="json",
    )
    assert adjacent.status_code == 201


def test_cancel_frees_interval_and_second_cancel_fails(api, resource, times):
    created = api.post("/api/v1/bookings/", payload(resource, times), format="json")
    booking_id = created.data["id"]

    cancelled = api.post(f"/api/v1/bookings/{booking_id}/cancel/")
    assert cancelled.status_code == 200
    assert cancelled.data["status"] == BookingStatus.CANCELLED

    second = api.post(f"/api/v1/bookings/{booking_id}/cancel/")
    assert second.status_code == 409
    assert second.data["error"]["code"] == "already_cancelled"

    assert api.post("/api/v1/bookings/", payload(resource, times), format="json").status_code == 201


def test_cannot_cancel_other_users_booking(api, other_user, resource, times):
    start, end = times
    foreign = Booking.objects.create(
        resource=resource, user=other_user, start_at=start, end_at=end, guests=1
    )
    response = api.post(f"/api/v1/bookings/{foreign.pk}/cancel/")
    assert response.status_code == 404
    foreign.refresh_from_db()
    assert foreign.status == BookingStatus.CONFIRMED


def test_validation_of_dates_guests_and_capacity(api, resource, times):
    start, end = times
    examples = [
        payload(resource, times, end_at=start.isoformat()),
        payload(resource, times, guests=0),
        payload(resource, times, guests=5),
        payload(
            resource,
            times,
            start_at=(start - timedelta(days=3)).isoformat(),
            end_at=(end - timedelta(days=3)).isoformat(),
        ),
    ]
    for data in examples:
        response = api.post("/api/v1/bookings/", data, format="json")
        assert response.status_code == 400, response.data
        assert set(response.data) == {"error"}
    assert Booking.objects.count() == 0


def test_inactive_resource_rejected(api, resource, times):
    resource.is_active = False
    resource.save(update_fields=["is_active"])
    response = api.post("/api/v1/bookings/", payload(resource, times), format="json")
    assert response.status_code == 400
    assert response.data["error"]["code"] == "resource_unavailable"


def test_past_booking_has_effective_completed_status(api, user, resource):
    end = timezone.now() - timedelta(hours=1)
    booking = Booking.objects.create(
        user=user,
        resource=resource,
        start_at=end - timedelta(hours=1),
        end_at=end,
        guests=1,
    )

    response = api.get(f"/api/v1/bookings/{booking.pk}/")
    assert response.status_code == 200
    assert response.data["status"] == BookingStatus.COMPLETED
    booking.refresh_from_db()
    assert booking.status == BookingStatus.CONFIRMED

    cancelled = api.post(f"/api/v1/bookings/{booking.pk}/cancel/")
    assert cancelled.status_code == 409
    assert cancelled.data["error"]["code"] == "booking_completed"
