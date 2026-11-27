import pytest
from rest_framework import serializers

from apps.accounts.models import User
from apps.common.pagination import PaginationInputSerializer, paginated_response_data

pytestmark = pytest.mark.django_db


class UsernameSerializer(serializers.Serializer):
    """Класс, представляющий пользователя одним логином для проверки пагинации"""

    username = serializers.CharField()


@pytest.fixture
def users() -> None:
    """Функция, создающая пять пользователей для разбиения на страницы"""

    for index in range(5):
        User.objects.create_user(username=f"user-{index}")


def _page(*, page: int, page_size: int) -> dict:
    """Функция, возвращающая страницу пользователей, отсортированных по логину"""

    return paginated_response_data(
        queryset=User.objects.order_by("username"),
        serializer_class=UsernameSerializer,
        page=page,
        page_size=page_size,
    )


def test_paginated_response_data_returns_page_and_total(users) -> None:
    """Функция, проверяющая формат ответа и выбор нужной страницы"""

    data = _page(page=2, page_size=2)

    assert data == {
        "count": 5,
        "page": 2,
        "page_size": 2,
        "results": [{"username": "user-2"}, {"username": "user-3"}],
    }


def test_paginated_response_data_returns_empty_results_after_last_page(users) -> None:
    """Функция, проверяющая пустую страницу за пределами списка при сохранении общего числа"""

    data = _page(page=4, page_size=2)

    assert data["count"] == 5
    assert data["results"] == []


@pytest.mark.parametrize(
    ("params", "is_valid"),
    [
        ({}, True),
        ({"page": "0"}, False),
        ({"page_size": "0"}, False),
        ({"page_size": "100"}, True),
        ({"page_size": "101"}, False),
    ],
)
def test_pagination_input_serializer_checks_bounds(params: dict, is_valid: bool) -> None:
    """Функция, проверяющая границы номера и размера страницы"""

    serializer = PaginationInputSerializer(data=params)

    assert serializer.is_valid() is is_valid
