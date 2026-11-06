import pytest
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient

from apps.accounts.models import Role, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user() -> User:
    """Функция, создающая администратора для проверки защищённого API"""

    return User.objects.create_user(username="admin", password="test-pass", role=Role.ADMIN)


@pytest.fixture
def admin_client(admin_user: User) -> APIClient:
    """Функция, создающая API-клиент с правами администратора"""

    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


def test_user_detail_returns_extended_fields(admin_client: APIClient) -> None:
    """Функция, проверяющая состав карточки, статус блокировки и отсутствие секретов"""

    user = User.objects.create_user(
        username="client",
        email="client@example.com",
        first_name="Анна",
        last_name="Петрова",
        role=Role.CLIENT,
    )
    user.is_blocked = True
    user.last_login = timezone.now()
    user.save(update_fields=["is_blocked", "last_login", "updated_at"])

    response = admin_client.get(reverse("admin-user-detail", args=[user.pk]))

    assert response.status_code == 200
    assert response.data == {
        "id": user.pk,
        "email": "client@example.com",
        "name": "Анна Петрова",
        "role": Role.CLIENT,
        "is_active": True,
        "is_blocked": True,
        "created_at": response.data["created_at"],
        "updated_at": response.data["updated_at"],
        "last_login": response.data["last_login"],
    }
    assert parse_datetime(response.data["created_at"]) == user.created_at
    assert parse_datetime(response.data["updated_at"]) == user.updated_at
    assert parse_datetime(response.data["last_login"]) == user.last_login
    assert "password" not in response.data


def test_user_detail_uses_username_when_name_is_empty(admin_client: APIClient) -> None:
    """Функция, проверяющая имя карточки при незаполненном профиле"""

    user = User.objects.create_user(username="no-name")

    response = admin_client.get(reverse("admin-user-detail", args=[user.pk]))

    assert response.status_code == 200
    assert response.data["name"] == "no-name"
    assert response.data["is_blocked"] is False
    assert response.data["last_login"] is None


def test_user_detail_returns_404_for_missing_id(admin_client: APIClient) -> None:
    """Функция, проверяющая ошибку для отсутствующего пользователя"""

    response = admin_client.get(reverse("admin-user-detail", args=[999999]))

    assert response.status_code == 404
    assert set(response.data) == {"code", "message", "details"}
    assert response.data["code"] == "NOT_FOUND"
    assert response.data["details"] == {}


@pytest.mark.parametrize("invalid_id", ["abc", "0", "-1", "1.5"])
def test_user_detail_returns_400_for_invalid_id(admin_client: APIClient, invalid_id: str) -> None:
    """Функция, проверяющая валидацию идентификатора из адреса запроса"""

    response = admin_client.get(reverse("admin-user-detail", args=[invalid_id]))

    assert response.status_code == 400
    assert set(response.data) == {"code", "message", "details"}
    assert response.data["code"] == "VALIDATION_ERROR"
    assert "id" in response.data["details"]


@pytest.mark.parametrize("role", [Role.CLIENT, Role.MANAGER])
def test_user_detail_denies_non_admin_roles(admin_user: User, role: str) -> None:
    """Функция, проверяющая запрет доступа клиенту и менеджеру"""

    user = User.objects.create_user(username=f"user-{role}", role=role)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("admin-user-detail", args=[admin_user.pk]))

    assert response.status_code == 403
    assert set(response.data) == {"code", "message", "details"}
    assert response.data["code"] == "ACCESS_DENIED"


def test_user_detail_denies_anonymous_client(admin_user: User) -> None:
    """Функция, проверяющая запрет доступа без аутентификации"""

    response = APIClient().get(reverse("admin-user-detail", args=[admin_user.pk]))

    assert response.status_code in (401, 403)
    assert response.data["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize("attribute", ["is_active", "is_blocked"])
def test_user_detail_denies_inactive_or_blocked_admin(admin_user: User, attribute: str) -> None:
    """Функция, проверяющая запрет доступа неактивному или заблокированному админу"""

    setattr(admin_user, attribute, attribute == "is_blocked")
    admin_user.save(update_fields=[attribute])
    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.get(reverse("admin-user-detail", args=[admin_user.pk]))

    assert response.status_code == 403
    assert response.data["code"] == "ACCESS_DENIED"
