import pytest

from apps.bookings.models import Category
from apps.bookings.selectors import category_list

pytestmark = pytest.mark.django_db


def test_category_selector_filters_before_pagination() -> None:
    """Функция, проверяющая выборку категорий без HTTP"""

    Category.objects.create(name="Room A", slug="room-a")
    second = Category.objects.create(name="Room B", slug="room-b")
    Category.objects.create(name="Table", slug="table")

    count, results = category_list(search="ROOM", page=2, page_size=1)

    assert count == 2
    assert list(results) == [second]
