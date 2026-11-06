from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission
from django.utils import timezone

from apps.bookings.models import Booking, BookingStatus

pytestmark = pytest.mark.django_db

CHANGELIST_URL = "/admin/bookings/booking/"


@pytest.fixture
def booking(user, resource, times) -> Booking:
    start, end = times
    return Booking.objects.create(
        resource=resource, user=user, start_at=start, end_at=end, guests=1
    )


@pytest.fixture
def past_booking(user, resource) -> Booking:
    end = timezone.now() - timedelta(hours=1)
    return Booking.objects.create(
        resource=resource, user=user, start_at=end - timedelta(hours=1), end_at=end, guests=1
    )


def cancel(client, *bookings):
    return client.post(
        CHANGELIST_URL,
        {"action": "cancel_bookings", "_selected_action": [booking.pk for booking in bookings]},
        follow=True,
    )


def test_changelist_shows_effective_status(admin_client, booking, past_booking):
    response = admin_client.get(CHANGELIST_URL)

    assert response.status_code == 200
    assert BookingStatus.CONFIRMED.label in response.text
    assert BookingStatus.COMPLETED.label in response.text


def test_effective_status_filter(admin_client, booking, past_booking):
    response = admin_client.get(CHANGELIST_URL, {"effective_status": BookingStatus.COMPLETED})

    assert list(response.context["cl"].result_list) == [past_booking]


def test_add_change_and_delete_are_forbidden(admin_client, booking):
    assert admin_client.get(f"{CHANGELIST_URL}add/").status_code == 403
    assert admin_client.get(f"{CHANGELIST_URL}{booking.pk}/delete/").status_code == 403

    response = admin_client.post(f"{CHANGELIST_URL}{booking.pk}/change/", {"guests": 3})
    assert response.status_code == 403
    booking.refresh_from_db()
    assert booking.guests == 1


def test_change_page_is_read_only(admin_client, booking):
    response = admin_client.get(f"{CHANGELIST_URL}{booking.pk}/change/")

    assert response.status_code == 200
    assert response.context["has_change_permission"] is False


def test_cancel_action_uses_service(admin_client, booking, past_booking):
    response = cancel(admin_client, booking, past_booking)

    booking.refresh_from_db()
    past_booking.refresh_from_db()
    assert booking.status == BookingStatus.CANCELLED
    assert past_booking.status == BookingStatus.CONFIRMED
    texts = [str(message) for message in response.context["messages"]]
    assert "Отменено броней: 1" in texts
    assert f"Бронь {past_booking.pk}: Completed bookings cannot be cancelled." in texts


def test_cancel_action_requires_change_permission(client, django_user_model, booking):
    staff = django_user_model.objects.create_user(
        username="viewer", password="test-pass-789", is_staff=True
    )
    staff.user_permissions.add(Permission.objects.get(codename="view_booking"))
    client.force_login(staff)

    response = client.get(CHANGELIST_URL)
    assert response.status_code == 200
    assert "cancel_bookings" not in response.text

    cancel(client, booking)
    booking.refresh_from_db()
    assert booking.status == BookingStatus.CONFIRMED
