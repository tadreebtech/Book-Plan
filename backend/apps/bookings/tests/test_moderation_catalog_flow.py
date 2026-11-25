from collections.abc import Callable

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.bookings.models import ModerationStatus, Resource, ResourceModerationLog

pytestmark = pytest.mark.django_db


@pytest.fixture
def moderator() -> User:
    """Функция, создающая администратора для проверки модерации и каталога"""

    return User.objects.create_user(username="qa-moderator", role=Role.ADMIN)


@pytest.fixture
def admin_client(moderator: User) -> APIClient:
    """Функция, создающая клиент запросов администратора"""

    client = APIClient()
    client.force_authenticate(user=moderator)
    return client


@pytest.fixture
def catalog_client() -> APIClient:
    """Функция, создающая клиент запросов посетителя с ролью клиента"""

    client = APIClient()
    client.force_authenticate(user=User.objects.create_user(username="qa-customer"))
    return client


@pytest.mark.parametrize("is_active", [True, False])
def test_moderation_decisions_change_catalog_and_preserve_audit(
    admin_client: APIClient,
    catalog_client: APIClient,
    moderator: User,
    listing_factory: Callable[..., Resource],
    is_active: bool,
) -> None:
    """Функция, проверяющая каталог и историю после последовательных решений модератора"""

    resource = listing_factory(name="QA moderation resource", is_active=is_active)
    filters = {"search": "QA moderation", "category": resource.kind, "page_size": 1}
    initial = catalog_client.get("/api/v1/listings/", filters)
    assert initial.status_code == 200
    assert initial.json()["count"] == 0
    expected_statuses = []
    previous = ModerationStatus.PENDING
    for action, status, reason in [
        ("approve", ModerationStatus.APPROVED, ""),
        ("reject", ModerationStatus.REJECTED, "Уточните адрес"),
        ("approve", ModerationStatus.APPROVED, ""),
        ("hide", ModerationStatus.HIDDEN, ""),
        ("approve", ModerationStatus.APPROVED, ""),
    ]:
        before = timezone.now()
        result = admin_client.post(
            f"/api/v1/admin/listings/{resource.pk}/{action}/",
            {"rejection_reason": reason},
            format="json",
        )
        assert result.status_code == 200
        resource.refresh_from_db()
        assert resource.is_active is is_active
        assert resource.moderation_status == status
        assert resource.rejection_reason == reason
        expected_statuses.append(status)
        events = ResourceModerationLog.objects.filter(resource_id=resource.pk).order_by("pk")
        assert list(events.values_list("moderation_status", flat=True)) == expected_statuses
        event = events.last()
        assert event.actor == moderator
        assert event.previous_status == previous
        assert event.rejection_reason == reason
        assert before <= event.created_at <= timezone.now()
        previous = status
        response = catalog_client.get("/api/v1/listings/", filters)
        assert response.status_code == 200
        expected_ids = [resource.pk] if is_active and status == ModerationStatus.APPROVED else []
        assert response.json()["count"] == len(expected_ids)
        assert [row["id"] for row in response.json()["results"]] == expected_ids


@pytest.mark.parametrize("payload", [{}, {"rejection_reason": ""}, {"rejection_reason": "  \n"}])
def test_invalid_rejection_keeps_published_resource_and_audit(
    admin_client: APIClient,
    catalog_client: APIClient,
    listing_factory: Callable[..., Resource],
    payload: dict,
) -> None:
    """Функция, проверяющая сохранение опубликованного объявления при неверной причине"""

    resource = listing_factory()
    url = f"/api/v1/admin/listings/{resource.pk}/"
    assert admin_client.post(url + "approve/").status_code == 200
    before_resource = Resource.objects.values().get(pk=resource.pk)
    before_events = list(ResourceModerationLog.objects.order_by("pk").values())
    response = admin_client.post(url + "reject/", payload, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert Resource.objects.values().get(pk=resource.pk) == before_resource
    assert list(ResourceModerationLog.objects.order_by("pk").values()) == before_events
    visible = catalog_client.get("/api/v1/listings/")
    assert visible.status_code == 200
    assert [row["id"] for row in visible.json()["results"]] == [resource.pk]


@pytest.mark.parametrize("role", [Role.CLIENT, Role.MANAGER])
@pytest.mark.parametrize("action", ["approve", "reject", "hide"])
def test_non_admin_cannot_change_published_resource(
    role: str, action: str, listing_factory: Callable[..., Resource]
) -> None:
    """Функция, проверяющая сохранность публикации и аудита при отказе в доступе"""

    user = User.objects.create_user(username="qa-denied", role=role)
    resource = listing_factory(manager=user, moderation_status=ModerationStatus.APPROVED)
    before = Resource.objects.values().get(pk=resource.pk)
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/v1/admin/listings/{resource.pk}/{action}/",
        {"rejection_reason": "Изменить описание"},
        format="json",
    )
    assert response.status_code == 403
    assert response.json()["code"] == "ACCESS_DENIED"
    assert Resource.objects.values().get(pk=resource.pk) == before
    assert not ResourceModerationLog.objects.exists()
