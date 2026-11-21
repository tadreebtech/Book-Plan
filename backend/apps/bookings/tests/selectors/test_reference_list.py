import pytest

from apps.bookings.models import Reference
from apps.bookings.selectors import reference_list

pytestmark = pytest.mark.django_db


def test_reference_selector_filters_and_paginates() -> None:
    """Функция, проверяющая фильтрацию справочников без HTTP"""

    Reference.objects.create(type="location_type", value="A")
    second = Reference.objects.create(type="location_type", value="B")
    Reference.objects.create(type="equipment_unit", value="C")

    count, values = reference_list(reference_type="location_type", page=2, page_size=1)

    assert count == 2
    assert list(values) == [second]
