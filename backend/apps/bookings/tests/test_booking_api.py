from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.exceptions import BookingConflict, BookingValidationError, ResourceUnavailable
from apps.bookings.models import Booking, BookingStatus, Resource, ResourceKind
from apps.bookings.services import cancel_booking, create_booking

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
    assert denied.data["error"]["code"] == "NOT_FOUND"


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
    assert conflicting.data["error"]["code"] == "BOOKING_CONFLICT"

    adjacent = api.post(
        "/api/v1/bookings/",
        payload(
            resource, times, start_at=end.isoformat(), end_at=(end + timedelta(hours=1)).isoformat()
        ),
        format="json",
    )
    assert adjacent.status_code == 201


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/api/v1/bookings/abc/"),
        ("post", "/api/v1/bookings/abc/cancel/"),
    ],
)
def test_invalid_booking_id_returns_not_found(api, method, path):
    response = getattr(api, method)(path)
    assert response.status_code == 404
    assert response.data["error"]["code"] == "NOT_FOUND"


def test_cancel_frees_interval_and_second_cancel_fails(api, resource, times):
    created = api.post("/api/v1/bookings/", payload(resource, times), format="json")
    booking_id = created.data["id"]

    cancelled = api.post(f"/api/v1/bookings/{booking_id}/cancel/")
    assert cancelled.status_code == 200
    assert cancelled.data["status"] == BookingStatus.CANCELLED

    second = api.post(f"/api/v1/bookings/{booking_id}/cancel/")
    assert second.status_code == 409
    assert second.data["error"]["code"] == "ALREADY_CANCELLED"

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
        (payload(resource, times, end_at=start.isoformat()), "VALIDATION_ERROR"),
        (payload(resource, times, guests=0), "VALIDATION_ERROR"),
        (payload(resource, times, guests=5), "CAPACITY_EXCEEDED"),
        (
            payload(
                resource,
                times,
                start_at=(start - timedelta(days=3)).isoformat(),
                end_at=(end - timedelta(days=3)).isoformat(),
            ),
            "INVALID_BOOKING",
        ),
    ]
    for data, expected_code in examples:
        response = api.post("/api/v1/bookings/", data, format="json")
        assert response.status_code == 400, response.data
        assert set(response.data) == {"error"}
        assert response.data["error"]["code"] == expected_code
    assert Booking.objects.count() == 0


def test_inactive_resource_rejected(api, resource, times):
    resource.is_active = False
    resource.save(update_fields=["is_active"])
    response = api.post("/api/v1/bookings/", payload(resource, times), format="json")
    assert response.status_code == 400
    assert response.data["error"]["code"] == "RESOURCE_UNAVAILABLE"


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
    assert cancelled.data["error"]["code"] == "BOOKING_COMPLETED"


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/api/v1/bookings/999999/"),
        ("post", "/api/v1/bookings/999999/cancel/"),
    ],
)
def test_missing_booking_returns_not_found(api, method, path):
    response = getattr(api, method)(path)
    assert response.status_code == 404
    assert response.data["error"]["code"] == "NOT_FOUND"


def test_cancel_requires_authentication(user, resource, times):
    start, end = times
    booking = Booking.objects.create(
        user=user, resource=resource, start_at=start, end_at=end, guests=1
    )
    response = APIClient().post(f"/api/v1/bookings/{booking.pk}/cancel/")
    assert response.status_code in (401, 403)
    booking.refresh_from_db()
    assert booking.status == BookingStatus.CONFIRMED


@pytest.mark.parametrize("case", ["past_start", "invalid_interval", "no_guests", "naive_start"])
def test_service_validates_without_serializer(user, resource, times, case):
    start, end = times
    guests = 2
    if case == "past_start":
        start = timezone.now() - timedelta(hours=1)
    elif case == "invalid_interval":
        end = start
    elif case == "no_guests":
        guests = 0
    elif case == "naive_start":
        start = timezone.make_naive(start)

    with pytest.raises(BookingValidationError) as exc:
        create_booking(user=user, resource=resource, start_at=start, end_at=end, guests=guests)
    assert exc.value.get_codes() == "INVALID_BOOKING"
    assert not Booking.objects.exists()


@pytest.mark.parametrize(
    "attribute, value, exception_class, expected_code",
    [
        ("is_active", False, ResourceUnavailable, "RESOURCE_UNAVAILABLE"),
        ("capacity", 1, BookingValidationError, "CAPACITY_EXCEEDED"),
    ],
)
def test_service_rechecks_resource_state(
    user, resource, times, attribute, value, exception_class, expected_code
):
    setattr(resource, attribute, value)
    resource.save(update_fields=[attribute])
    start, end = times

    with pytest.raises(exception_class) as exc:
        create_booking(user=user, resource=resource, start_at=start, end_at=end, guests=2)
    assert exc.value.get_codes() == expected_code
    assert not Booking.objects.exists()


def test_service_rejects_cancellation_of_elapsed_booking(user, resource):
    end = timezone.now() - timedelta(hours=1)
    booking = Booking.objects.create(
        user=user,
        resource=resource,
        start_at=end - timedelta(hours=1),
        end_at=end,
        guests=1,
    )
    with pytest.raises(BookingConflict) as exc:
        cancel_booking(user=user, booking_id=booking.pk)

    assert exc.value.get_codes() == "BOOKING_COMPLETED"
    booking.refresh_from_db()
    assert booking.status == BookingStatus.CONFIRMED
