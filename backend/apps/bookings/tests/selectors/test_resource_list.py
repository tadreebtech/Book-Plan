from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.bookings.models import ModerationStatus, ResourceKind
from apps.bookings.selectors import resource_list

pytestmark = pytest.mark.django_db


def test_resource_list_filters_and_counts_before_pagination(listing_factory):
    """Функция, проверяющая фильтры и количество объявлений без HTTP"""

    provider = User.objects.create_user(username="provider", role=Role.MANAGER)
    fields = {"manager": provider, "moderation_status": ModerationStatus.APPROVED}
    matches = [listing_factory(**fields) for _ in range(3)]
    listing_factory(manager=provider)
    listing_factory(kind=ResourceKind.HOTEL_ROOM, **fields)
    listing_factory(moderation_status=ModerationStatus.APPROVED)
    listing_factory(name="Lecture hall", **fields)

    count, listings = resource_list(
        moderation_status=ModerationStatus.APPROVED,
        category=ResourceKind.UNIVERSITY_ROOM,
        provider=provider.pk,
        search="MEETING",
        page=2,
        page_size=2,
    )

    assert count == 3
    assert list(listings) == [matches[0]]


def test_resource_list_orders_pages_by_creation_date_and_id(listing_factory):
    """Функция, проверяющая устойчивую сортировку страниц при совпадении дат"""

    now = timezone.now()
    first = listing_factory(created_at=now)
    second = listing_factory(created_at=now)
    older = listing_factory(created_at=now - timedelta(days=1))

    count, first_page = resource_list(page_size=2)
    next_count, second_page = resource_list(page=2, page_size=2)

    assert count == next_count == 3
    assert list(first_page) == [second, first]
    assert list(second_page) == [older]


def test_resource_list_returns_empty_page_for_empty_selection():
    """Функция, проверяющая пустую страницу при отсутствии объявлений"""

    count, listings = resource_list()

    assert count == 0
    assert list(listings) == []


def test_resource_list_handles_page_beyond_database_integer_range(listing_factory):
    """Функция, проверяющая пустой результат для очень большого номера страницы"""

    listing_factory()

    count, listings = resource_list(page=10**30)

    assert count == 1
    assert list(listings) == []


def test_resource_list_defaults_to_twenty_results(listing_factory):
    """Функция, проверяющая размер страницы по умолчанию"""

    for _ in range(21):
        listing_factory()

    count, listings = resource_list()

    assert count == 21
    assert len(listings) == 20
