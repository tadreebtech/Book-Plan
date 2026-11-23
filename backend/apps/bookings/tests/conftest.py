from collections.abc import Callable

import pytest

from apps.bookings.models import Resource, ResourceKind


@pytest.fixture
def listing_factory() -> Callable[..., Resource]:
    """Функция, предоставляющая создание объявлений для тестов"""

    def create_listing(**fields: object) -> Resource:
        """Функция, создающая объявление с указанными свойствами"""

        defaults = {"name": "Meeting room", "kind": ResourceKind.UNIVERSITY_ROOM, "capacity": 4}
        return Resource.objects.create(**(defaults | fields))

    return create_listing
