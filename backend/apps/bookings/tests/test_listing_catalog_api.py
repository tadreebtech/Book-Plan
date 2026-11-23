from collections.abc import Callable

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.bookings.models import ModerationStatus, Resource, ResourceKind

pytestmark = pytest.mark.django_db
CATALOG_URL = "/api/v1/listings/"
PROVIDER_LISTINGS_URL = "/api/v1/provider/listings/"
REJECTION_REASON = "Проверьте адрес помещения"


@pytest.fixture
def provider() -> User:
    """Функция, создающая поставщика объявлений"""

    return User.objects.create_user(username="provider", role=Role.MANAGER)


@pytest.fixture
def provider_listings(
    provider: User, listing_factory: Callable[..., Resource]
) -> dict[ModerationStatus, Resource]:
    """Функция, создающая по одному объявлению поставщика в каждом статусе"""

    admin = User.objects.create_user(username="moderator", role=Role.ADMIN)
    return {
        ModerationStatus.PENDING: listing_factory(manager=provider),
        ModerationStatus.APPROVED: listing_factory(
            manager=provider, moderation_status=ModerationStatus.APPROVED
        ),
        ModerationStatus.REJECTED: listing_factory(
            manager=provider,
            moderation_status=ModerationStatus.REJECTED,
            rejection_reason=REJECTION_REASON,
            moderated_at=timezone.now(),
            moderated_by=admin,
        ),
        ModerationStatus.HIDDEN: listing_factory(
            manager=provider, moderation_status=ModerationStatus.HIDDEN, is_active=False
        ),
    }


@pytest.mark.parametrize("role", [Role.CLIENT, Role.MANAGER])
def test_catalog_lists_only_active_approved_listings(
    role: Role,
    provider: User,
    provider_listings: dict[ModerationStatus, Resource],
    listing_factory: Callable[..., Resource],
) -> None:
    """Функция, проверяющая видимость в каталоге для клиента и владельца объявлений"""

    client = APIClient()
    user = provider if role == Role.MANAGER else User.objects.create_user(username="client")
    client.force_authenticate(user=user)
    approved = provider_listings[ModerationStatus.APPROVED]
    listing_factory(moderation_status=ModerationStatus.APPROVED, is_active=False)
    listing_factory(moderation_status=ModerationStatus.HIDDEN)

    response = client.get(CATALOG_URL)

    assert response.status_code == 200
    assert response.json() == {
        "count": 1,
        "page": 1,
        "page_size": 20,
        "results": [
            {
                "id": approved.pk,
                "title": approved.name,
                "category": approved.kind,
                "capacity": approved.capacity,
            }
        ],
    }


def test_catalog_applies_moderation_before_search_pagination(
    provider: User, listing_factory: Callable[..., Resource]
) -> None:
    """Функция, проверяющая фильтрацию и количество результатов до разбиения на страницы"""

    client = APIClient()
    client.force_authenticate(user=provider)
    approved_fields = {"moderation_status": ModerationStatus.APPROVED}
    first = listing_factory(**approved_fields)
    second = listing_factory(**approved_fields)
    listing_factory(name="Hotel meeting room", kind=ResourceKind.HOTEL_ROOM, **approved_fields)
    listing_factory(name="Lecture hall", **approved_fields)
    listing_factory()
    filters = {
        "category": ResourceKind.UNIVERSITY_ROOM,
        "search": "MEETING",
        "page_size": 1,
        "moderation_status": ModerationStatus.PENDING,
    }

    first_page = client.get(CATALOG_URL, filters)
    second_page = client.get(CATALOG_URL, filters | {"page": 2})

    assert first_page.status_code == second_page.status_code == 200
    assert first_page.json()["count"] == second_page.json()["count"] == 2
    assert [row["id"] for row in first_page.json()["results"]] == [second.pk]
    assert [row["id"] for row in second_page.json()["results"]] == [first.pk]


def test_provider_lists_own_listings_in_all_statuses(
    provider: User,
    provider_listings: dict[ModerationStatus, Resource],
    listing_factory: Callable[..., Resource],
) -> None:
    """Функция, проверяющая статусы, причину отклонения и изоляцию объявлений поставщика"""

    client = APIClient()
    client.force_authenticate(user=provider)
    other_provider = User.objects.create_user(username="other_provider", role=Role.MANAGER)
    listing_factory(manager=other_provider, moderation_status=ModerationStatus.APPROVED)
    listing_factory(manager=other_provider)
    listing_factory()

    response = client.get(
        PROVIDER_LISTINGS_URL,
        {"provider": other_provider.pk, "moderation_status": ModerationStatus.APPROVED},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == len(provider_listings)
    assert {listing["id"] for listing in data["results"]} == {
        listing.pk for listing in provider_listings.values()
    }
    rows = {listing["moderation_status"]: listing for listing in data["results"]}
    assert rows.keys() == provider_listings.keys()
    assert rows[ModerationStatus.REJECTED]["rejection_reason"] == REJECTION_REASON
    assert rows[ModerationStatus.HIDDEN]["is_active"] is False


@pytest.mark.parametrize("url", [CATALOG_URL, PROVIDER_LISTINGS_URL])
def test_listing_endpoints_require_authentication(url: str) -> None:
    """Функция, проверяющая требование аутентификации для обоих списков"""

    response = APIClient().get(url)

    assert response.status_code == 403
    assert response.json()["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize(
    ("role", "is_active"),
    [(Role.CLIENT, True), (Role.ADMIN, True), (Role.MANAGER, False)],
)
def test_provider_listing_requires_active_manager(role: Role, is_active: bool) -> None:
    """Функция, проверяющая доступ к списку только для активного поставщика"""

    client = APIClient()
    user = User.objects.create_user(username="user", role=role, is_active=is_active)
    client.force_authenticate(user=user)

    response = client.get(PROVIDER_LISTINGS_URL)

    assert response.status_code == 403
    assert response.json()["code"] == "ACCESS_DENIED"
