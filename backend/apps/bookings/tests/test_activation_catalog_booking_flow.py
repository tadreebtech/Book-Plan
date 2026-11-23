from collections.abc import Callable
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.bookings.models import (
    Booking,
    ModerationStatus,
    Resource,
    ResourceActivationLog,
    ResourceKind,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def actor() -> User:
    """Функция, создающая администратора для проверки активности ресурса"""

    return User.objects.create_user(username="activation-admin", role=Role.ADMIN)


@pytest.fixture
def admin_client(actor: User) -> APIClient:
    """Функция, создающая клиент запросов администратора"""

    client = APIClient()
    client.force_authenticate(user=actor)
    return client


@pytest.mark.parametrize("kind", ResourceKind.values)
def test_activation_round_trip_updates_catalog_and_booking_access(
    kind: str,
    actor: User,
    admin_client: APIClient,
    listing_factory: Callable[..., Resource],
) -> None:
    """Функция, проверяющая отключение и включение ресурса через каталог и бронирование"""

    provider = User.objects.create_user(username="owner", role=Role.MANAGER)
    other = User.objects.create_user(username="other-owner", role=Role.MANAGER)
    customer = User.objects.create_user(username="booking-client")
    client = APIClient()
    client.force_authenticate(user=customer)
    owner_client = APIClient()
    owner_client.force_authenticate(user=provider)
    resource = listing_factory(
        name="QA activation resource",
        kind=kind,
        manager=provider,
        moderation_status=ModerationStatus.APPROVED,
    )
    foreign = listing_factory(manager=other, is_active=False)
    start = timezone.now() + timedelta(days=10)
    payload = {
        "resource": resource.pk,
        "start_at": start.isoformat(),
        "end_at": (start + timedelta(hours=1)).isoformat(),
        "guests": 1,
    }
    first = client.post("/api/v1/bookings/", payload, format="json")
    assert first.status_code == 201
    original = Booking.objects.values().get(pk=first.json()["id"])
    filters = {"category": kind, "search": "QA activation", "page_size": 1}
    initial = client.get("/api/v1/listings/", filters)
    assert initial.status_code == 200
    assert [row["id"] for row in initial.json()["results"]] == [resource.pk]

    before = timezone.now()
    deactivate = admin_client.post(f"/api/v1/admin/listings/{resource.pk}/deactivate/")
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False
    assert deactivate.json()["upcoming_bookings"] == 1
    assert Booking.objects.values().get(pk=original["id"]) == original
    hidden = client.get("/api/v1/listings/", filters)
    assert hidden.status_code == 200
    assert hidden.json()["count"] == 0
    assert hidden.json()["results"] == []
    owner_response = owner_client.get("/api/v1/provider/listings/", {"provider": other.pk})
    assert owner_response.status_code == 200
    assert [row["id"] for row in owner_response.json()["results"]] == [resource.pk]
    assert owner_response.json()["results"][0]["is_active"] is False
    admin_response = admin_client.get("/api/v1/admin/listings/")
    assert admin_response.status_code == 200
    assert {row["id"] for row in admin_response.json()["results"]} == {resource.pk, foreign.pk}

    payload["start_at"] = (start + timedelta(days=1)).isoformat()
    payload["end_at"] = (start + timedelta(days=1, hours=1)).isoformat()
    blocked = client.post("/api/v1/bookings/", payload, format="json")
    assert blocked.status_code in (400, 409)
    assert list(Booking.objects.values()) == [original]
    inactive_state = Resource.objects.values().get(pk=resource.pk)
    assert admin_client.post(f"/api/v1/admin/listings/{resource.pk}/deactivate/").status_code == 200
    assert Resource.objects.values().get(pk=resource.pk) == inactive_state
    assert ResourceActivationLog.objects.count() == 1

    activate = admin_client.post(f"/api/v1/admin/listings/{resource.pk}/activate/")
    assert activate.status_code == 200
    assert activate.json()["is_active"] is True
    restored = client.get("/api/v1/listings/", filters)
    assert restored.status_code == 200
    assert restored.json()["count"] == 1
    assert [row["id"] for row in restored.json()["results"]] == [resource.pk]
    assert admin_client.post(f"/api/v1/admin/listings/{resource.pk}/activate/").status_code == 200
    booked = client.post("/api/v1/bookings/", payload, format="json")
    assert booked.status_code == 201
    assert Booking.objects.count() == 2
    assert Booking.objects.values().get(pk=original["id"]) == original
    events = list(ResourceActivationLog.objects.order_by("pk"))
    assert [event.action for event in events] == ["DEACTIVATED", "ACTIVATED"]
    for event in events:
        assert event.actor == actor
        assert event.resource_id == resource.pk
        assert before <= event.created_at <= timezone.now()


@pytest.mark.parametrize("role", [Role.CLIENT, Role.MANAGER])
@pytest.mark.parametrize(("action", "is_active"), [("activate", False), ("deactivate", True)])
def test_non_admin_cannot_switch_activity_or_write_audit(
    role: str, action: str, is_active: bool, listing_factory: Callable[..., Resource]
) -> None:
    """Функция, проверяющая оба действия для клиента и владельца ресурса"""

    user = User.objects.create_user(username="denied-user", role=role)
    resource = listing_factory(manager=user, is_active=is_active)
    before = Resource.objects.values().get(pk=resource.pk)
    client = APIClient()
    client.force_authenticate(user=user)
    result = client.post(f"/api/v1/admin/listings/{resource.pk}/{action}/")
    assert result.status_code == 403
    assert result.json()["code"] == "ACCESS_DENIED"
    assert Resource.objects.values().get(pk=resource.pk) == before
    assert not ResourceActivationLog.objects.exists()


@pytest.mark.parametrize("resource_id", ["abc", "0", "-1", "9223372036854775808"])
def test_activate_rejects_invalid_identifier_without_audit(
    admin_client: APIClient, resource_id: str
) -> None:
    """Функция, проверяющая ошибку идентификатора при включении ресурса"""

    result = admin_client.post(f"/api/v1/admin/listings/{resource_id}/activate/")
    assert result.status_code == 400
    assert result.json()["code"] == "VALIDATION_ERROR"
    assert not ResourceActivationLog.objects.exists()


@pytest.mark.xfail(
    strict=True,
    reason="TG-125: audit actions differ from acceptance criteria; see docs/qa-tg119-tg125.md",
)
@pytest.mark.parametrize(
    ("action", "is_active", "expected_action"),
    [("activate", False, "ACTIVATE_RESOURCE"), ("deactivate", True, "DEACTIVATE_RESOURCE")],
)
def test_activation_audit_action_matches_tg125_acceptance_criteria(
    admin_client: APIClient,
    listing_factory: Callable[..., Resource],
    action: str,
    is_active: bool,
    expected_action: str,
) -> None:
    """Функция, фиксирующая расхождение названий событий с критериями задания №125"""

    resource = listing_factory(is_active=is_active)
    response = admin_client.post(f"/api/v1/admin/listings/{resource.pk}/{action}/")
    assert response.status_code == 200
    assert ResourceActivationLog.objects.get(resource_id=resource.pk).action == expected_action
