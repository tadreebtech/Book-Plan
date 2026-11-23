from unittest.mock import Mock

import pytest
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.bookings.models import ModerationStatus, ResourceModerationLog

pytestmark = pytest.mark.django_db
LISTINGS_URL = "/api/v1/admin/listings/"


@pytest.fixture
def moderator() -> User:
    """Функция, создающая пользователя с ролью администратора"""

    return User.objects.create_user(username="moderator", role=Role.ADMIN)


@pytest.fixture
def admin_client(moderator: User) -> APIClient:
    """Функция, создающая API-клиент администратора"""

    client = APIClient()
    client.force_authenticate(user=moderator)
    return client


@pytest.mark.parametrize(
    ("action", "payload", "new_status", "reason"),
    [
        ("approve", {}, ModerationStatus.APPROVED, ""),
        (
            "reject",
            {"rejection_reason": "  Неверное описание.\n"},
            ModerationStatus.REJECTED,
            "Неверное описание.",
        ),
        ("hide", {}, ModerationStatus.HIDDEN, ""),
    ],
)
def test_admin_can_moderate_listing(
    admin_client, moderator, listing_factory, action, payload, new_status, reason
):
    """Функция, проверяющая ответ API, сохранённое решение и запись аудита"""

    listing = listing_factory()
    before = timezone.now()

    response = admin_client.post(f"{LISTINGS_URL}{listing.pk}/{action}/", payload, format="json")

    assert response.status_code == 200
    listing.refresh_from_db()
    assert listing.moderation_status == new_status
    assert listing.rejection_reason == reason
    assert listing.moderated_by == moderator
    assert before <= listing.moderated_at <= listing.updated_at

    data = response.json()
    assert data == {
        "id": listing.pk,
        "moderation_status": new_status,
        "rejection_reason": reason,
        "moderated_at": data["moderated_at"],
        "moderated_by": moderator.pk,
    }
    assert parse_datetime(data["moderated_at"]) == listing.moderated_at

    event = ResourceModerationLog.objects.get(resource_id=listing.pk)
    assert event.actor == moderator
    assert event.previous_status == ModerationStatus.PENDING
    assert event.moderation_status == new_status
    assert event.rejection_reason == reason
    assert event.created_at == listing.moderated_at


@pytest.mark.parametrize("action", ["approve", "hide"])
def test_next_decision_clears_current_reason_and_preserves_audit(
    admin_client, listing_factory, action
):
    """Функция, проверяющая историю решений после смены статуса отклонённого объявления"""

    listing = listing_factory()
    url = f"{LISTINGS_URL}{listing.pk}/"
    rejected = admin_client.post(
        f"{url}reject/", {"rejection_reason": "Wrong address."}, format="json"
    )
    assert rejected.status_code == 200

    response = admin_client.post(f"{url}{action}/")

    assert response.status_code == 200
    listing.refresh_from_db()
    assert listing.rejection_reason == ""
    events = ResourceModerationLog.objects.filter(resource_id=listing.pk).order_by("pk")
    rejected_event, next_event = events
    assert rejected_event.rejection_reason == "Wrong address."
    assert next_event.previous_status == ModerationStatus.REJECTED
    assert next_event.moderation_status == listing.moderation_status
    assert next_event.rejection_reason == ""


def test_moderation_log_survives_listing_deletion(admin_client, listing_factory):
    """Функция, проверяющая сохранение аудита после удаления объявления"""

    listing = listing_factory()
    resource_id = listing.pk
    response = admin_client.post(f"{LISTINGS_URL}{resource_id}/hide/")
    assert response.status_code == 200

    listing.delete()

    event = ResourceModerationLog.objects.get(resource_id=resource_id)
    assert event.moderation_status == ModerationStatus.HIDDEN


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"rejection_reason": ""},
        {"rejection_reason": " \t\n"},
        {"rejection_reason": None},
        {"rejection_reason": 123},
    ],
)
def test_reject_requires_nonblank_text(admin_client, listing_factory, payload):
    """Функция, проверяющая ошибку валидации причины и отсутствие изменений"""

    listing = listing_factory()

    response = admin_client.post(f"{LISTINGS_URL}{listing.pk}/reject/", payload, format="json")

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "rejection_reason" in response.json()["details"]
    listing.refresh_from_db()
    assert listing.moderation_status == ModerationStatus.PENDING
    assert listing.moderated_at is None
    assert not ResourceModerationLog.objects.exists()


@pytest.mark.parametrize("action", ["approve", "reject", "hide"])
@pytest.mark.parametrize(
    "resource_id", ["missing", "-1", "0", "1.0", "9223372036854775807", "9223372036854775808"]
)
def test_invalid_or_unknown_listing_returns_404(admin_client, action, resource_id):
    """Функция, проверяющая единый ответ для неизвестных и неверных идентификаторов"""

    payload = {"rejection_reason": "Wrong address."} if action == "reject" else {}
    response = admin_client.post(f"{LISTINGS_URL}{resource_id}/{action}/", payload, format="json")

    assert response.status_code == 404
    assert response.json() == {
        "code": "NOT_FOUND",
        "message": "Requested object not found.",
        "details": {},
    }
    assert not ResourceModerationLog.objects.exists()


@pytest.mark.parametrize("action", ["approve", "reject", "hide"])
@pytest.mark.parametrize(
    ("user_fields", "code"),
    [
        (None, "UNAUTHORIZED"),
        ({"role": Role.CLIENT, "is_staff": True}, "ACCESS_DENIED"),
        ({"role": Role.MANAGER}, "ACCESS_DENIED"),
        ({"role": Role.ADMIN, "is_active": False}, "ACCESS_DENIED"),
    ],
)
def test_moderation_requires_active_admin(listing_factory, action, user_fields, code):
    """Функция, проверяющая права администратора для каждой операции модерации"""

    client = APIClient()
    if user_fields is not None:
        client.force_authenticate(user=User.objects.create_user(username="denied", **user_fields))
    listing = listing_factory()

    payload = {"rejection_reason": "Wrong address."} if action == "reject" else {}
    response = client.post(f"{LISTINGS_URL}{listing.pk}/{action}/", payload, format="json")

    assert response.status_code == 403
    assert response.json()["code"] == code
    listing.refresh_from_db()
    assert listing.moderation_status == ModerationStatus.PENDING
    assert not ResourceModerationLog.objects.exists()


def test_moderation_rolls_back_when_audit_write_fails(admin_client, listing_factory, monkeypatch):
    """Функция, проверяющая откат модерации при сбое записи аудита"""

    listing = listing_factory()
    original_updated_at = listing.updated_at
    write_log = Mock(side_effect=RuntimeError("Simulated audit write failure"))
    monkeypatch.setattr(ResourceModerationLog, "save", write_log)

    response = admin_client.post(f"{LISTINGS_URL}{listing.pk}/approve/")

    write_log.assert_called_once()
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    listing.refresh_from_db()
    assert listing.moderation_status == ModerationStatus.PENDING
    assert listing.moderated_at is None
    assert listing.moderated_by is None
    assert listing.updated_at == original_updated_at
    assert not ResourceModerationLog.objects.exists()
