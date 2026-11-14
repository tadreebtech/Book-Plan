from datetime import timedelta

import pytest
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.bookings.models import ModerationStatus, Resource, ResourceKind

pytestmark = pytest.mark.django_db
LISTINGS_URL = "/api/v1/admin/listings/"


@pytest.fixture
def admin_client():
    admin = User.objects.create_user(username="admin", role=Role.ADMIN)
    client = APIClient()
    client.force_authenticate(user=admin)
    return client


@pytest.fixture
def listing_factory():
    def create_listing(**fields):
        defaults = {"name": "Meeting room", "kind": ResourceKind.UNIVERSITY_ROOM, "capacity": 4}
        return Resource.objects.create(**(defaults | fields))

    return create_listing


def test_admin_listing_filters_can_be_combined(admin_client, listing_factory):
    provider = User.objects.create_user(username="provider", role=Role.MANAGER)
    matching_fields = {
        "manager": provider,
        "moderation_status": ModerationStatus.APPROVED,
    }
    match = listing_factory(**matching_fields)
    listing_factory(manager=provider)
    listing_factory(kind=ResourceKind.HOTEL_ROOM, **matching_fields)
    listing_factory(moderation_status=ModerationStatus.APPROVED)
    listing_factory(name="Lecture hall", **matching_fields)

    response = admin_client.get(
        LISTINGS_URL,
        {
            "moderation_status": ModerationStatus.APPROVED,
            "category": ResourceKind.UNIVERSITY_ROOM,
            "provider": provider.pk,
            "search": "MEETING",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 20
    listing = data["results"][0]
    assert listing == {
        "id": match.pk,
        "title": match.name,
        "category": match.kind,
        "provider": provider.pk,
        "moderation_status": match.moderation_status,
        "created_at": listing["created_at"],
    }
    assert parse_datetime(listing["created_at"]) == match.created_at


def test_admin_listing_paginates_in_stable_creation_order(admin_client, listing_factory):
    now = timezone.now()
    first = listing_factory(created_at=now)
    second = listing_factory(created_at=now, moderation_status=ModerationStatus.HIDDEN)
    older = listing_factory(created_at=now - timedelta(days=1))

    page_one = admin_client.get(LISTINGS_URL, {"page_size": 2}).json()
    page_two = admin_client.get(LISTINGS_URL, {"page_size": 2, "page": 2}).json()
    beyond = admin_client.get(LISTINGS_URL, {"page_size": 2, "page": 3}).json()

    assert page_one["count"] == page_two["count"] == beyond["count"] == 3
    assert [row["id"] for row in page_one["results"]] == [second.pk, first.pk]
    assert [row["id"] for row in page_two["results"]] == [older.pk]
    assert page_two["results"][0]["provider"] is None
    assert beyond["results"] == []


@pytest.mark.parametrize(
    "user_fields",
    [
        None,
        {"role": Role.CLIENT, "is_staff": True},
        {"role": Role.MANAGER},
        {"role": Role.ADMIN, "is_active": False},
    ],
)
def test_admin_listing_rejects_users_without_active_admin_role(user_fields):
    client = APIClient()
    if user_fields is not None:
        client.force_authenticate(user=User.objects.create_user(username="denied", **user_fields))

    assert client.get(LISTINGS_URL).status_code in (401, 403)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("moderation_status", "UNKNOWN"),
        ("category", "UNKNOWN"),
        ("provider", 0),
        ("page", 0),
        ("page_size", 101),
    ],
)
def test_admin_listing_validates_query_parameters(admin_client, field, value):
    response = admin_client.get(LISTINGS_URL, {field: value})

    assert response.status_code == 400
    assert field in response.json()
