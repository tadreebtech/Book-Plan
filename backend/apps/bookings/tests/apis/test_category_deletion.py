from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.bookings.exceptions import ResourceUnavailable
from apps.bookings.models import Booking, Category, Resource, ResourceKind, ResourceStatus
from apps.bookings.services import create_booking

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client() -> APIClient:
    """Функция, создающая клиент администратора для проверки удаления"""

    client = APIClient()
    client.force_authenticate(user=User.objects.create_user(username="admin", role=Role.ADMIN))
    return client


def test_category_delete_counts_all_non_archived_listings(admin_client: APIClient) -> None:
    """Функция, проверяющая запрет удаления независимо от деактивации объявления"""

    category = Category.objects.create(name="Rooms", slug="rooms")
    for status, active in [
        (ResourceStatus.ACTIVE, True),
        (ResourceStatus.ACTIVE, False),
        (ResourceStatus.ARCHIVED, True),
    ]:
        Resource.objects.create(
            name="Room",
            kind=ResourceKind.HOTEL_ROOM,
            capacity=2,
            category=category,
            status=status,
            is_active=active,
        )

    response = admin_client.delete(f"/api/v1/admin/categories/{category.pk}/")

    assert response.status_code == 409
    assert response.data["code"] == "CATEGORY_IN_USE"
    assert "2 non-archived listing(s)" in response.data["message"]
    assert set(response.data) == {"code", "message", "details"}
    assert category.resources.count() == 3


def test_category_delete_preserves_archived_resources_and_bookings(admin_client: APIClient) -> None:
    """Функция, проверяющая удаление категории с сохранением архивного объявления и броней"""

    category = Category.objects.create(name="Rooms", slug="rooms")
    resource = Resource.objects.create(
        name="Room",
        kind=ResourceKind.HOTEL_ROOM,
        capacity=2,
        category=category,
        status=ResourceStatus.ARCHIVED,
    )
    user = User.objects.create_user(username="client")
    start = timezone.now() + timedelta(days=1)
    booking = Booking.objects.create(
        resource=resource,
        user=user,
        start_at=start,
        end_at=start + timedelta(hours=1),
        guests=1,
    )

    response = admin_client.delete(f"/api/v1/admin/categories/{category.pk}/")

    assert response.status_code == 204
    assert not Category.objects.filter(pk=category.pk).exists()
    resource.refresh_from_db()
    assert resource.category_id is None
    assert resource.status == ResourceStatus.ARCHIVED
    assert Booking.objects.get(pk=booking.pk).resource_id == resource.pk


def test_archived_listing_cannot_receive_a_new_booking() -> None:
    """Функция, проверяющая недоступность архивного объявления для нового бронирования"""

    resource = Resource.objects.create(
        name="Room",
        kind=ResourceKind.HOTEL_ROOM,
        capacity=2,
        status=ResourceStatus.ARCHIVED,
    )
    user = User.objects.create_user(username="client")
    start = timezone.now() + timedelta(days=1)

    with pytest.raises(ResourceUnavailable):
        create_booking(
            user=user,
            resource=resource,
            start_at=start,
            end_at=start + timedelta(hours=1),
            guests=1,
        )
    assert not Booking.objects.exists()
