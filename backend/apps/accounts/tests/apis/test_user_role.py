import pytest
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.test import APIClient

from apps.accounts.models import AuditAction, AuditLog, Role, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user() -> User:
    """Функция, создающая администратора для проверки смены роли"""

    return User.objects.create_user(username="admin", password="test-pass", role=Role.ADMIN)


@pytest.fixture
def admin_client(admin_user: User) -> APIClient:
    """Функция, создающая клиент с правами администратора"""

    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def target_user() -> User:
    """Функция, создающая клиента, роль которого меняется"""

    return User.objects.create_user(username="target", role=Role.CLIENT)


def patch_role(client: APIClient, user_id: int, body: dict) -> Response:
    """Функция, отправляющая запрос смены роли пользователя"""

    return client.patch(reverse("admin-user-role", args=[user_id]), body, format="json")


@pytest.mark.parametrize(
    ("value", "old_role", "expected_role"),
    [
        ("Client", Role.MANAGER, Role.CLIENT),
        ("Provider", Role.CLIENT, Role.MANAGER),
        ("Admin", Role.CLIENT, Role.ADMIN),
    ],
)
def test_role_change_updates_role_and_audit(
        admin_client: APIClient,
        admin_user: User,
        value: str,
        old_role: str,
        expected_role: str,
) -> None:
    """Функция, проверяющая смену роли и запись автора, цели, старой и новой роли в аудит"""

    target = User.objects.create_user(username="subject", role=old_role)

    response = patch_role(admin_client, target.pk, {"role": value})
    target.refresh_from_db()

    assert response.status_code == 200
    assert response.data == {"id": target.pk, "role": expected_role}
    assert target.role == expected_role
    audit_log = AuditLog.objects.get()
    assert audit_log.actor_id == admin_user.pk
    assert audit_log.target_id == target.pk
    assert audit_log.action == AuditAction.CHANGE_ROLE
    assert audit_log.old_value == old_role
    assert audit_log.new_value == expected_role


def test_role_change_applies_to_next_request(admin_client: APIClient, target_user: User) -> None:
    """Функция, проверяющая немедленное действие новой роли на следующем запросе"""

    patch_role(admin_client, target_user.pk, {"role": "Admin"})
    client = APIClient()
    client.force_authenticate(user=User.objects.get(pk=target_user.pk))

    response = client.get(reverse("admin-user-list"))

    assert response.status_code == 200


def test_same_role_does_not_create_audit(admin_client: APIClient, target_user: User) -> None:
    """Функция, проверяющая повторную установку роли без записи в аудит"""

    response = patch_role(admin_client, target_user.pk, {"role": "Client"})

    assert response.status_code == 200
    assert response.data["role"] == Role.CLIENT
    assert AuditLog.objects.count() == 0


@pytest.mark.parametrize("body", [{"role": "Superuser"}, {"role": ""}, {"role": None}, {}])
def test_invalid_role_returns_400(admin_client: APIClient, target_user: User, body: dict) -> None:
    """Функция, проверяющая ошибку 400 для неверной или пустой роли без изменений в базе"""

    response = patch_role(admin_client, target_user.pk, body)
    target_user.refresh_from_db()

    assert response.status_code == 400
    assert response.data["code"] == "VALIDATION_ERROR"
    assert "role" in response.data["details"]
    assert target_user.role == Role.CLIENT
    assert AuditLog.objects.count() == 0


def test_missing_user_returns_404(admin_client: APIClient) -> None:
    """Функция, проверяющая ошибку 404 для несуществующего пользователя"""

    response = patch_role(admin_client, 999999, {"role": "Client"})

    assert response.status_code == 404
    assert response.data["code"] == "NOT_FOUND"
    assert AuditLog.objects.count() == 0


@pytest.mark.parametrize("role", [Role.CLIENT, Role.MANAGER])
def test_non_admin_gets_403(role: str, target_user: User) -> None:
    """Функция, проверяющая запрет смены роли для клиента и менеджера"""

    client = APIClient()
    client.force_authenticate(user=User.objects.create_user(username="other", role=role))

    response = patch_role(client, target_user.pk, {"role": "Admin"})
    target_user.refresh_from_db()

    assert response.status_code == 403
    assert response.data["code"] == "ACCESS_DENIED"
    assert target_user.role == Role.CLIENT
    assert AuditLog.objects.count() == 0


def test_anonymous_gets_403(target_user: User) -> None:
    """Функция, проверяющая запрет смены роли без аутентификации"""

    response = patch_role(APIClient(), target_user.pk, {"role": "Admin"})

    assert response.status_code == 403
    assert response.data["code"] == "UNAUTHORIZED"
    assert AuditLog.objects.count() == 0


def test_inactive_admin_gets_403(admin_user: User, target_user: User) -> None:
    """Функция, проверяющая запрет смены роли для неактивного администратора"""

    admin_user.is_active = False
    admin_user.save(update_fields=["is_active"])
    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = patch_role(client, target_user.pk, {"role": "Admin"})

    assert response.status_code == 403
    assert response.data["code"] == "ACCESS_DENIED"
