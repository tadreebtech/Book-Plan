from base64 import b64encode

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AuditAction, AuditLog, Role, User

pytestmark = pytest.mark.django_db

UNAUTHORIZED_RESPONSE = {
    "code": "UNAUTHORIZED",
    "message": "Authentication is required.",
    "details": {},
}


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


@pytest.fixture
def target_password(target_user: User) -> str:
    """Функция, задающая пароль пользователя для проверки входа"""

    password = "test-pass"
    target_user.set_password(password)
    target_user.save(update_fields=["password"])
    return password


def _basic_auth_header(*, username: str, password: str) -> str:
    """Функция, формирующая заголовок Basic Authentication для запроса"""

    credentials = b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {credentials}"


def test_blocked_user_cannot_log_in_or_use_existing_session(
    admin_client: APIClient, target_user: User, target_password: str
) -> None:
    """Функция, проверяющая отказ во входе и доступе до разблокировки"""

    credentials = {"username": target_user.username, "password": target_password}
    bookings_url = reverse("booking-list")
    existing_session = APIClient()
    fresh_session = APIClient()

    assert existing_session.login(**credentials)
    assert existing_session.get(bookings_url).status_code == 200

    assert admin_client.post(reverse("admin-user-block", args=[target_user.pk])).status_code == 200

    assert not fresh_session.login(**credentials)
    denied_read = existing_session.get(bookings_url)
    denied_write = existing_session.post(bookings_url, {}, format="json")
    for response in (denied_read, denied_write):
        assert response.status_code == 403
        assert response.data == UNAUTHORIZED_RESPONSE

    response = admin_client.post(reverse("admin-user-unblock", args=[target_user.pk]))
    assert response.status_code == 200
    assert fresh_session.login(**credentials)
    assert fresh_session.get(bookings_url).status_code == 200
    assert existing_session.get(bookings_url).status_code == 200


def test_basic_authentication_rejects_blocked_user_without_revealing_status(
    admin_client: APIClient, target_user: User, target_password: str
) -> None:
    """Функция, проверяющая одинаковый ответ при блокировке и неверных учётных данных"""

    client = APIClient()
    bookings_url = reverse("booking-list")
    valid_auth = _basic_auth_header(username=target_user.username, password=target_password)
    wrong_password = _basic_auth_header(username=target_user.username, password="wrong-password")
    unknown_user = _basic_auth_header(username="unknown-user", password=target_password)

    assert client.get(bookings_url, HTTP_AUTHORIZATION=valid_auth).status_code == 200
    denied_password = client.get(bookings_url, HTTP_AUTHORIZATION=wrong_password)
    denied_username = client.get(bookings_url, HTTP_AUTHORIZATION=unknown_user)

    assert admin_client.post(reverse("admin-user-block", args=[target_user.pk])).status_code == 200
    denied_blocked = client.get(bookings_url, HTTP_AUTHORIZATION=valid_auth)

    for response in (denied_blocked, denied_password, denied_username):
        assert response.status_code == 403
        assert response.data == UNAUTHORIZED_RESPONSE


def test_block_creates_audit_record(
    admin_client: APIClient, admin_user: User, target_user: User
) -> None:
    """Функция, проверяющая блокировку и запись автора, действия, цели и времени"""

    before_request = timezone.now()
    response = admin_client.post(reverse("admin-user-block", args=[target_user.pk]))
    target_user.refresh_from_db()

    assert response.status_code == 200
    assert response.data == {"id": target_user.pk, "is_active": False}
    assert target_user.is_active is False

    audit_log = AuditLog.objects.get()
    assert audit_log.actor_id == admin_user.pk
    assert audit_log.target_id == target_user.pk
    assert audit_log.action == AuditAction.USER_BLOCKED
    assert before_request <= audit_log.created_at <= timezone.now()


def test_unblock_creates_audit_record(
    admin_client: APIClient, admin_user: User, target_user: User
) -> None:
    """Функция, проверяющая снятие блокировки и запись действия в аудит"""

    target_user.is_active = False
    target_user.save(update_fields=["is_active"])

    response = admin_client.post(reverse("admin-user-unblock", args=[target_user.pk]))
    target_user.refresh_from_db()

    assert response.status_code == 200
    assert response.data == {"id": target_user.pk, "is_active": True}
    assert target_user.is_active is True
    audit_log = AuditLog.objects.get()
    assert audit_log.actor_id == admin_user.pk
    assert audit_log.target_id == target_user.pk
    assert audit_log.action == AuditAction.USER_UNBLOCKED


def test_block_then_unblock_restores_active_state(
    admin_client: APIClient, target_user: User
) -> None:
    """Функция, проверяющая восстановление активности после разблокировки"""

    admin_client.post(reverse("admin-user-block", args=[target_user.pk]))
    admin_client.post(reverse("admin-user-unblock", args=[target_user.pk]))
    target_user.refresh_from_db()

    assert target_user.is_active is True
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
    assert target_user.is_active is True
    assert AuditLog.objects.count() == 0


@pytest.mark.parametrize(
    ("route_name", "initially_active"),
    [("admin-user-block", False), ("admin-user-unblock", True)],
)
def test_repeated_status_change_is_idempotent(
    admin_client: APIClient, target_user: User, route_name: str, initially_active: bool
) -> None:
    """Функция, проверяющая повторное действие без изменения времени и аудита"""

    target_user.is_active = initially_active
    target_user.save(update_fields=["is_active"])
    original_updated_at = target_user.updated_at

    response = admin_client.post(reverse(route_name, args=[target_user.pk]))
    target_user.refresh_from_db()

    assert response.status_code == 200
    assert response.data == {"id": target_user.pk, "is_active": initially_active}
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
    assert admin_user.is_active is True
    assert AuditLog.objects.count() == 0


def test_admin_cannot_block_other_admin(admin_client: APIClient) -> None:
    """Функция, проверяющая защиту другого администратора от блокировки"""

    other_admin = User.objects.create_user(username="other-admin", role=Role.ADMIN)

    response = admin_client.post(reverse("admin-user-block", args=[other_admin.pk]))
    other_admin.refresh_from_db()

    assert response.status_code == 403
    assert response.data["code"] == "ACCESS_DENIED"
    assert other_admin.is_active is True
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

    assert response.status_code == 403
    assert response.data["code"] == "UNAUTHORIZED"
    assert AuditLog.objects.count() == 0


@pytest.mark.parametrize("route_name", ["admin-user-block", "admin-user-unblock"])
def test_inactive_admin_cannot_change_status(
    admin_user: User, target_user: User, route_name: str
) -> None:
    """Функция, проверяющая запрет изменения статуса неактивному админу"""

    admin_user.is_active = False
    admin_user.save(update_fields=["is_active"])
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
