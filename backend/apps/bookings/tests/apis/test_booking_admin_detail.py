from datetime import datetime

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.bookings.models import Booking, Resource, ResourceKind

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user() -> User:
    """Функция, создающая администратора для проверки защищённого API"""

    return User.objects.create_user(
        username="admin", email="admin@example.com", password="test-pass", role=Role.ADMIN
    )


@pytest.fixture
def admin_client(admin_user: User) -> APIClient:
    """Функция, создающая API-клиент с правами администратора"""

    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def manager() -> User:
    """Функция, создающая менеджера, за которым закреплён ресурс"""

    return User.objects.create_user(
        username="manager", email="manager@example.com", role=Role.MANAGER
    )


@pytest.fixture
def client_user() -> User:
    """Функция, создающая клиента, который оформил бронь"""

    return User.objects.create_user(
        username="client", email="client@example.com", first_name="Анна", last_name="Петрова"
    )


def _book(*, resource: Resource, user: User) -> Booking:
    """Функция, сохраняющая бронь напрямую в базе данных для подготовки теста"""

    return Booking.objects.create(
        resource=resource,
        user=user,
        start_at=timezone.make_aware(datetime(2026, 12, 1, 10)),
        end_at=timezone.make_aware(datetime(2026, 12, 1, 12)),
        guests=3,
    )


def test_booking_detail_returns_extended_fields(
    admin_client: APIClient, manager: User, client_user: User
) -> None:
    """Функция, проверяющая расширенные данные клиента, ресурса, менеджера и периода"""

    room = Resource.objects.create(
        kind=ResourceKind.UNIVERSITY_ROOM, name="Аудитория 101", capacity=10, manager=manager
    )
    booking = _book(resource=room, user=client_user)

    response = admin_client.get(reverse("admin-booking-detail", args=[booking.id]))

    assert response.status_code == 200
    data = response.data
    assert set(data) == {
        "id",
        "client",
        "resource",
        "provider",
        "period",
        "guests",
        "status",
        "created_at",
        "updated_at",
    }
    assert data["id"] == booking.id
    assert data["client"] == {
        "id": client_user.id,
        "email": "client@example.com",
        "name": "Анна Петрова",
    }
    assert data["resource"] == {
        "id": room.id,
        "name": "Аудитория 101",
        "kind": "UNIVERSITY_ROOM",
        "capacity": 10,
        "is_active": True,
    }
    assert data["provider"] == {"id": manager.id, "email": "manager@example.com", "name": "manager"}
    assert set(data["period"]) == {"start_at", "end_at"}
    assert data["guests"] == 3
    assert data["status"] == "CONFIRMED"


def test_booking_detail_returns_null_provider_without_manager(
    admin_client: APIClient, client_user: User
) -> None:
    """Функция, проверяющая пустого менеджера у ресурса без закреплённого менеджера"""

    table = Resource.objects.create(kind=ResourceKind.RESTAURANT_TABLE, name="Столик", capacity=4)
    booking = _book(resource=table, user=client_user)

    response = admin_client.get(reverse("admin-booking-detail", args=[booking.id]))

    assert response.status_code == 200
    assert response.data["provider"] is None


def test_booking_detail_returns_not_found_for_missing_booking(admin_client: APIClient) -> None:
    """Функция, проверяющая ответ 404 в едином формате для несуществующей брони"""

    response = admin_client.get(reverse("admin-booking-detail", args=[999999]))

    assert response.status_code == 404
    assert response.data == {
        "code": "NOT_FOUND",
        "message": "Requested object not found.",
        "details": {},
    }


@pytest.mark.parametrize("booking_id", ["abc", "0", "-1"])
def test_booking_detail_validates_identifier(admin_client: APIClient, booking_id: str) -> None:
    """Функция, проверяющая ошибку проверки данных для неверного идентификатора"""

    response = admin_client.get(reverse("admin-booking-detail", args=[booking_id]))

    assert response.status_code == 400
    assert response.data["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_booking_detail_is_read_only(
    admin_client: APIClient, client_user: User, method: str
) -> None:
    """Функция, проверяющая, что карточку брони нельзя изменить через API"""

    table = Resource.objects.create(kind=ResourceKind.RESTAURANT_TABLE, name="Столик", capacity=4)
    booking = _book(resource=table, user=client_user)

    response = getattr(admin_client, method)(reverse("admin-booking-detail", args=[booking.id]))

    assert response.status_code == 405
    assert Booking.objects.filter(pk=booking.id).exists()


@pytest.mark.parametrize("role", [Role.CLIENT, Role.MANAGER])
def test_booking_detail_rejects_non_admin_roles(role: str, client_user: User) -> None:
    """Функция, проверяющая запрет доступа клиенту и менеджеру, даже к собственной брони"""

    user = User.objects.create_user(username=f"user-{role}", role=role)
    table = Resource.objects.create(kind=ResourceKind.RESTAURANT_TABLE, name="Столик", capacity=4)
    booking = _book(resource=table, user=user)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("admin-booking-detail", args=[booking.id]))

    assert response.status_code == 403
    assert response.data["code"] == "ACCESS_DENIED"


def test_booking_detail_rejects_anonymous_user(client_user: User) -> None:
    """Функция, проверяющая запрет доступа без входа в систему"""

    table = Resource.objects.create(kind=ResourceKind.RESTAURANT_TABLE, name="Столик", capacity=4)
    booking = _book(resource=table, user=client_user)

    response = APIClient().get(reverse("admin-booking-detail", args=[booking.id]))

    assert response.status_code in (401, 403)
