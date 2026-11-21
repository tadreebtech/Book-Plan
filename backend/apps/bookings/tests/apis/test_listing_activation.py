from datetime import timedelta
from unittest.mock import Mock

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.bookings.models import (
    Booking,
    BookingStatus,
    Resource,
    ResourceActivationAction,
    ResourceActivationLog,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user() -> User:
    """Функция, создающая администратора для проверки защищённого API"""

    return User.objects.create_user(username="admin", role=Role.ADMIN)


@pytest.fixture
def admin_client(admin_user: User) -> APIClient:
    """Функция, создающая API-клиент с правами администратора"""

    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


def _url(action: str, resource_id: object) -> str:
    """Функция, возвращающая адрес активации или деактивации ресурса"""

    return reverse(f"admin-listing-{action}", args=[resource_id])


def _book(*, resource: Resource, days: int, status: str = BookingStatus.CONFIRMED) -> Booking:
    """Функция, сохраняющая часовую бронь ресурса со сдвигом в днях от текущего момента"""

    start = timezone.now() + timedelta(days=days)
    user = User.objects.create_user(username=f"client-{days}-{status}")
    return Booking.objects.create(
        resource=resource,
        user=user,
        start_at=start,
        end_at=start + timedelta(hours=1),
        guests=1,
        status=status,
    )


def test_deactivate_turns_resource_off_and_writes_log(
    admin_client: APIClient, admin_user: User, listing_factory
) -> None:
    """Функция, проверяющая деактивацию ресурса и запись в журнал"""

    resource = listing_factory()

    response = admin_client.post(_url("deactivate", resource.pk))

    assert response.status_code == 200
    assert response.data == {"id": resource.pk, "is_active": False, "upcoming_bookings": 0}
    resource.refresh_from_db()
    assert resource.is_active is False
    log = ResourceActivationLog.objects.get()
    assert (log.resource_id, log.actor, log.action) == (
        resource.pk,
        admin_user,
        ResourceActivationAction.DEACTIVATED,
    )


def test_activate_turns_resource_on_and_writes_log(
    admin_client: APIClient, listing_factory
) -> None:
    """Функция, проверяющая активацию ресурса и запись в журнал"""

    resource = listing_factory(is_active=False)

    response = admin_client.post(_url("activate", resource.pk))

    assert response.status_code == 200
    assert response.data["is_active"] is True
    resource.refresh_from_db()
    assert resource.is_active is True
    assert ResourceActivationLog.objects.get().action == ResourceActivationAction.ACTIVATED


def test_deactivate_keeps_confirmed_bookings(admin_client: APIClient, listing_factory) -> None:
    """Функция, проверяющая, что деактивация не отменяет подтверждённые брони"""

    resource = listing_factory()
    upcoming = _book(resource=resource, days=1)
    _book(resource=resource, days=2, status=BookingStatus.CANCELLED)
    _book(resource=resource, days=-2)

    response = admin_client.post(_url("deactivate", resource.pk))

    assert response.data["upcoming_bookings"] == 1
    upcoming.refresh_from_db()
    assert upcoming.status == BookingStatus.CONFIRMED
    assert Booking.objects.filter(status=BookingStatus.CONFIRMED).count() == 2


@pytest.mark.parametrize(("action", "is_active"), [("activate", True), ("deactivate", False)])
def test_repeated_action_does_not_write_log(
    admin_client: APIClient, listing_factory, action: str, is_active: bool
) -> None:
    """Функция, проверяющая, что действие без изменения состояния не попадает в журнал"""

    resource = listing_factory(is_active=is_active)

    response = admin_client.post(_url(action, resource.pk))

    assert response.status_code == 200
    assert response.data["is_active"] is is_active
    assert not ResourceActivationLog.objects.exists()


def test_deactivate_rolls_back_when_log_write_fails(
    admin_client: APIClient, listing_factory, monkeypatch
) -> None:
    """Функция, проверяющая, что ресурс не меняется, если запись в журнал не сохранилась"""

    resource = listing_factory()
    monkeypatch.setattr(
        ResourceActivationLog, "save", Mock(side_effect=RuntimeError("Simulated log failure"))
    )

    response = admin_client.post(_url("deactivate", resource.pk))

    assert response.status_code == 500
    resource.refresh_from_db()
    assert resource.is_active is True


@pytest.mark.parametrize("action", ["activate", "deactivate"])
def test_missing_resource_returns_not_found(admin_client: APIClient, action: str) -> None:
    """Функция, проверяющая ответ 404 для несуществующего ресурса"""

    response = admin_client.post(_url(action, 999999))

    assert response.status_code == 404
    assert response.data["code"] == "NOT_FOUND"


@pytest.mark.parametrize("resource_id", ["abc", "0", "-1", "9223372036854775808"])
def test_invalid_identifier_returns_validation_error(
    admin_client: APIClient, resource_id: str
) -> None:
    """Функция, проверяющая ошибку проверки данных для неверного идентификатора"""

    response = admin_client.post(_url("deactivate", resource_id))

    assert response.status_code == 400
    assert response.data["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_only_post_is_allowed(admin_client: APIClient, listing_factory, method: str) -> None:
    """Функция, проверяющая, что смена активности доступна только методом POST"""

    resource = listing_factory()

    response = getattr(admin_client, method)(_url("deactivate", resource.pk))

    assert response.status_code == 405
    assert response.data["code"] == "METHOD_NOT_ALLOWED"


@pytest.mark.parametrize("role", [Role.CLIENT, Role.MANAGER])
def test_non_admin_roles_are_denied(listing_factory, role: str) -> None:
    """Функция, проверяющая запрет смены активности клиенту и менеджеру"""

    resource = listing_factory()
    client = APIClient()
    client.force_authenticate(user=User.objects.create_user(username=f"user-{role}", role=role))

    response = client.post(_url("deactivate", resource.pk))

    assert response.status_code == 403
    assert response.data["code"] == "ACCESS_DENIED"
    resource.refresh_from_db()
    assert resource.is_active is True


def test_anonymous_user_is_denied(listing_factory) -> None:
    """Функция, проверяющая запрет смены активности без входа в систему"""

    resource = listing_factory()

    response = APIClient().post(_url("deactivate", resource.pk))

    assert response.status_code == 403
    assert response.data["code"] == "UNAUTHORIZED"


def test_inactive_admin_is_denied(admin_user: User, listing_factory) -> None:
    """Функция, проверяющая запрет смены активности заблокированному администратору"""

    resource = listing_factory()
    admin_user.is_active = False
    admin_user.save(update_fields=["is_active"])
    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.post(_url("deactivate", resource.pk))

    assert response.status_code == 403
    assert response.data["code"] == "ACCESS_DENIED"
