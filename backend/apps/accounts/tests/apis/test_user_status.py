import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AuditAction, AuditLog, Role, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user() -> User:
    """Функция, создающая администратора для проверки управления статусом"""

    return User.objects.create_user(username="admin", password="test-pass", role=Role.ADMIN)


@pytest.fixture
def admin_client(admin_user: User) -> APIClient:
    """Функция, создающая клиент с правами администратора"""

    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def target_user() -> User:
    """Функция, создающая пользователя для изменения статуса"""

    return User.objects.create_user(username="target", role=Role.CLIENT)


def test_block_creates_audit_record(
    admin_client: APIClient, admin_user: User, target_user: User
) -> None:
    """Функция, проверяющая блокировку и запись автора, действия, цели и времени"""

    before_request = timezone.now()
    response = admin_client.post(reverse("admin-user-block", args=[target_user.pk]))
    target_user.refresh_from_db()

    assert response.status_code == 200
    assert response.data == {"id": target_user.pk, "is_blocked": True}
    assert target_user.is_blocked is True
    assert target_user.is_active is True

    audit_log = AuditLog.objects.get()
    assert audit_log.actor_id == admin_user.pk
    assert audit_log.target_id == target_user.pk
    assert audit_log.action == AuditAction.USER_BLOCKED
    assert before_request <= audit_log.created_at <= timezone.now()


def test_unblock_creates_audit_record(
    admin_client: APIClient, admin_user: User, target_user: User
) -> None:
    """Функция, проверяющая снятие блокировки и запись действия в аудит"""

    target_user.is_blocked = True
    target_user.save(update_fields=["is_blocked"])

    response = admin_client.post(reverse("admin-user-unblock", args=[target_user.pk]))
    target_user.refresh_from_db()

    assert response.status_code == 200
    assert response.data == {"id": target_user.pk, "is_blocked": False}
    assert target_user.is_blocked is False
    audit_log = AuditLog.objects.get()
    assert audit_log.actor_id == admin_user.pk
    assert audit_log.target_id == target_user.pk
    assert audit_log.action == AuditAction.USER_UNBLOCKED


def test_status_change_preserves_inactive_state(admin_client: APIClient, target_user: User) -> None:
    """Функция, проверяющая сохранение независимого признака активности пользователя"""

    target_user.is_active = False
    target_user.save(update_fields=["is_active"])

    admin_client.post(reverse("admin-user-block", args=[target_user.pk]))
    admin_client.post(reverse("admin-user-unblock", args=[target_user.pk]))
    target_user.refresh_from_db()

    assert target_user.is_active is False
    assert target_user.is_blocked is False
    assert list(AuditLog.objects.order_by("pk").values_list("action", flat=True)) == [
        AuditAction.USER_BLOCKED,
        AuditAction.USER_UNBLOCKED,
    ]


def test_audit_failure_rolls_back_block(
    admin_client: APIClient, target_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Функция, проверяющая откат блокировки при невозможности записать аудит"""

    def fail_audit_save(self: AuditLog, *args: object, **kwargs: object) -> None:
        """Функция, имитирующая ошибку при сохранении записи аудита"""

        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(AuditLog, "save", fail_audit_save)

    response = admin_client.post(reverse("admin-user-block", args=[target_user.pk]))
    target_user.refresh_from_db()

    assert response.status_code == 500
    assert target_user.is_blocked is False
    assert AuditLog.objects.count() == 0


@pytest.mark.parametrize(
    ("route_name", "initially_blocked"),
    [("admin-user-block", True), ("admin-user-unblock", False)],
)
def test_repeated_status_change_is_idempotent(
    admin_client: APIClient, target_user: User, route_name: str, initially_blocked: bool
) -> None:
    """Функция, проверяющая повторное действие без изменения времени и аудита"""

    target_user.is_blocked = initially_blocked
    target_user.save(update_fields=["is_blocked"])
    original_updated_at = target_user.updated_at

    response = admin_client.post(reverse(route_name, args=[target_user.pk]))
    target_user.refresh_from_db()

    assert response.status_code == 200
    assert response.data == {"id": target_user.pk, "is_blocked": initially_blocked}
    assert target_user.updated_at == original_updated_at
    assert AuditLog.objects.count() == 0


@pytest.mark.parametrize("target_role", [Role.CLIENT, Role.MANAGER])
def test_block_allows_non_admin_roles(admin_client: APIClient, target_role: str) -> None:
    """Функция, проверяющая возможность блокировки клиента и менеджера"""

    user = User.objects.create_user(username=f"target-{target_role}", role=target_role)

    response = admin_client.post(reverse("admin-user-block", args=[user.pk]))

    assert response.status_code == 200
    assert AuditLog.objects.filter(target=user, action=AuditAction.USER_BLOCKED).exists()


@pytest.mark.parametrize("route_name", ["admin-user-block", "admin-user-unblock"])
def test_status_change_returns_404_for_missing_user(
    admin_client: APIClient, route_name: str
) -> None:
    """Функция, проверяющая ответ для отсутствующего пользователя без записи аудита"""

    response = admin_client.post(reverse(route_name, args=[999999]))

    assert response.status_code == 404
    assert response.data["code"] == "NOT_FOUND"
    assert AuditLog.objects.count() == 0


@pytest.mark.parametrize("route_name", ["admin-user-block", "admin-user-unblock"])
@pytest.mark.parametrize("invalid_id", ["abc", "0", "-1"])
def test_status_change_rejects_invalid_id(
    admin_client: APIClient, route_name: str, invalid_id: str
) -> None:
    """Функция, проверяющая формат ошибки для неверного идентификатора"""

    response = admin_client.post(reverse(route_name, args=[invalid_id]))

    assert response.status_code == 400
    assert response.data["code"] == "VALIDATION_ERROR"
    assert "id" in response.data["details"]


def test_admin_cannot_block_self(admin_client: APIClient, admin_user: User) -> None:
    """Функция, проверяющая защиту администратора от собственной блокировки"""

    response = admin_client.post(reverse("admin-user-block", args=[admin_user.pk]))
    admin_user.refresh_from_db()

    assert response.status_code == 403
    assert response.data["code"] == "ACCESS_DENIED"
    assert admin_user.is_blocked is False
    assert AuditLog.objects.count() == 0


def test_admin_cannot_block_other_admin(admin_client: APIClient) -> None:
    """Функция, проверяющая защиту другого администратора от блокировки"""

    other_admin = User.objects.create_user(username="other-admin", role=Role.ADMIN)

    response = admin_client.post(reverse("admin-user-block", args=[other_admin.pk]))
    other_admin.refresh_from_db()

    assert response.status_code == 403
    assert response.data["code"] == "ACCESS_DENIED"
    assert other_admin.is_blocked is False
    assert AuditLog.objects.count() == 0


@pytest.mark.parametrize("route_name", ["admin-user-block", "admin-user-unblock"])
@pytest.mark.parametrize("role", [Role.CLIENT, Role.MANAGER])
def test_non_admin_cannot_change_status(target_user: User, route_name: str, role: str) -> None:
    """Функция, проверяющая запрет изменения статуса клиенту и менеджеру"""

    requester = User.objects.create_user(username=f"requester-{role}", role=role)
    client = APIClient()
    client.force_authenticate(user=requester)

    response = client.post(reverse(route_name, args=[target_user.pk]))

    assert response.status_code == 403
    assert response.data["code"] == "ACCESS_DENIED"
    assert AuditLog.objects.count() == 0


@pytest.mark.parametrize("route_name", ["admin-user-block", "admin-user-unblock"])
def test_anonymous_cannot_change_status(target_user: User, route_name: str) -> None:
    """Функция, проверяющая запрет изменения статуса без входа"""

    response = APIClient().post(reverse(route_name, args=[target_user.pk]))

    assert response.status_code in (401, 403)
    assert response.data["code"] == "UNAUTHORIZED"
    assert AuditLog.objects.count() == 0


@pytest.mark.parametrize("route_name", ["admin-user-block", "admin-user-unblock"])
@pytest.mark.parametrize("attribute", ["is_active", "is_blocked"])
def test_inactive_or_blocked_admin_cannot_change_status(
    admin_user: User, target_user: User, route_name: str, attribute: str
) -> None:
    """Функция, проверяющая запрет для неактивного или заблокированного админа"""

    setattr(admin_user, attribute, attribute == "is_blocked")
    admin_user.save(update_fields=[attribute])
    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.post(reverse(route_name, args=[target_user.pk]))

    assert response.status_code == 403
    assert response.data["code"] == "ACCESS_DENIED"
    assert AuditLog.objects.count() == 0


@pytest.mark.parametrize("route_name", ["admin-user-block", "admin-user-unblock"])
def test_status_change_supports_post_only(
    admin_client: APIClient, target_user: User, route_name: str
) -> None:
    """Функция, проверяющая запрет GET-запроса к изменению статуса"""

    response = admin_client.get(reverse(route_name, args=[target_user.pk]))

    assert response.status_code == 405
    assert response.data["code"] == "METHOD_NOT_ALLOWED"
    assert AuditLog.objects.count() == 0
