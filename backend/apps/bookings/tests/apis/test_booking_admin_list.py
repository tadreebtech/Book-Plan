from datetime import datetime

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.bookings.models import Booking, BookingStatus, Resource, ResourceKind

pytestmark = pytest.mark.django_db


def _at(day: int, hour: int) -> datetime:
    """Функция, возвращающая момент времени в декабре 2026 года в часовом поясе проекта"""

    return timezone.make_aware(datetime(2026, 12, day, hour))


@pytest.fixture
def admin_user() -> User:
    """Функция, создающая администратора для проверки защищённого API"""

    return User.objects.create_user(
        username="admin", email="admin@example.com", password="test-pass", role=Role.ADMIN
    )


@pytest.fixture
def admin_client(admin_user: User) -> APIClient:
    """Функция, создающая API-клиент с правами администратора"""

    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def manager() -> User:
    """Функция, создающая менеджера, за которым закреплён ресурс"""

    return User.objects.create_user(username="manager", role=Role.MANAGER)


@pytest.fixture
def client_user() -> User:
    """Функция, создающая клиента, который оформляет брони"""

    return User.objects.create_user(
        username="client", email="client@example.com", first_name="Анна", last_name="Петрова"
    )


@pytest.fixture
def room(manager: User) -> Resource:
    """Функция, создающая аудиторию университета с менеджером"""

    return Resource.objects.create(
        kind=ResourceKind.UNIVERSITY_ROOM, name="Аудитория 101", capacity=10, manager=manager
    )


@pytest.fixture
def table() -> Resource:
    """Функция, создающая столик ресторана без менеджера"""

    return Resource.objects.create(kind=ResourceKind.RESTAURANT_TABLE, name="Столик 1", capacity=4)


def _book(
    *, resource: Resource, user: User, start: datetime, end: datetime, status: str = "CONFIRMED"
) -> Booking:
    """Функция, сохраняющая бронь напрямую в базе данных для подготовки теста"""

    return Booking.objects.create(
        resource=resource, user=user, start_at=start, end_at=end, guests=1, status=status
    )


def _ids(response) -> list[int]:
    """Функция, возвращающая идентификаторы броней из ответа API в порядке выдачи"""

    return [booking["id"] for booking in response.data["results"]]


def test_booking_list_returns_required_fields(
    admin_client: APIClient, room: Resource, client_user: User
) -> None:
    """Функция, проверяющая состав полей брони, клиента, ресурса и периода"""

    booking = _book(resource=room, user=client_user, start=_at(1, 10), end=_at(1, 12))

    response = admin_client.get(reverse("admin-booking-list"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["page"] == 1
    assert response.data["page_size"] == 20
    item = response.data["results"][0]
    assert set(item) == {"id", "client", "resource", "period", "status", "created_at"}
    assert item["id"] == booking.id
    assert item["client"] == {
        "id": client_user.id,
        "email": "client@example.com",
        "name": "Анна Петрова",
    }
    assert item["resource"] == {"id": room.id, "name": "Аудитория 101", "kind": "UNIVERSITY_ROOM"}
    assert set(item["period"]) == {"start_at", "end_at"}
    assert item["status"] == BookingStatus.CONFIRMED


def test_booking_list_shows_bookings_of_all_clients(
    admin_client: APIClient, room: Resource, client_user: User
) -> None:
    """Функция, проверяющая, что администратор видит брони всех клиентов платформы"""

    other = User.objects.create_user(username="other")
    first = _book(resource=room, user=client_user, start=_at(1, 10), end=_at(1, 12))
    second = _book(resource=room, user=other, start=_at(2, 10), end=_at(2, 12))

    response = admin_client.get(reverse("admin-booking-list"))

    assert set(_ids(response)) == {first.id, second.id}


def test_booking_list_paginates_without_duplicates(
    admin_client: APIClient, room: Resource, client_user: User
) -> None:
    """Функция, проверяющая размер страниц, общее количество и отсутствие повторов"""

    for day in range(1, 6):
        _book(resource=room, user=client_user, start=_at(day, 10), end=_at(day, 12))

    first = admin_client.get(reverse("admin-booking-list"), {"page": 1, "page_size": 2})
    second = admin_client.get(reverse("admin-booking-list"), {"page": 2, "page_size": 2})
    beyond = admin_client.get(reverse("admin-booking-list"), {"page": 4, "page_size": 2})

    assert first.data["count"] == second.data["count"] == beyond.data["count"] == 5
    assert len(_ids(first)) == len(_ids(second)) == 2
    assert set(_ids(first)).isdisjoint(_ids(second))
    assert beyond.data["results"] == []


def test_booking_list_filters_by_status(
    admin_client: APIClient, room: Resource, client_user: User
) -> None:
    """Функция, проверяющая фильтр по статусу брони"""

    _book(resource=room, user=client_user, start=_at(1, 10), end=_at(1, 12))
    cancelled = _book(
        resource=room, user=client_user, start=_at(2, 10), end=_at(2, 12), status="CANCELLED"
    )

    response = admin_client.get(reverse("admin-booking-list"), {"status": "CANCELLED"})

    assert _ids(response) == [cancelled.id]


def test_booking_list_filters_by_date_range(
    admin_client: APIClient, room: Resource, client_user: User
) -> None:
    """Функция, проверяющая выбор броней, период которых попадает в отрезок дат"""

    before = _book(resource=room, user=client_user, start=_at(1, 10), end=_at(1, 12))
    inside = _book(resource=room, user=client_user, start=_at(3, 10), end=_at(3, 12))
    crossing = _book(resource=room, user=client_user, start=_at(5, 22), end=_at(6, 2))
    after = _book(resource=room, user=client_user, start=_at(8, 10), end=_at(8, 12))

    both = admin_client.get(
        reverse("admin-booking-list"), {"date_from": "2026-12-02", "date_to": "2026-12-05"}
    )
    from_only = admin_client.get(reverse("admin-booking-list"), {"date_from": "2026-12-06"})
    to_only = admin_client.get(reverse("admin-booking-list"), {"date_to": "2026-12-01"})

    assert set(_ids(both)) == {inside.id, crossing.id}
    assert set(_ids(from_only)) == {crossing.id, after.id}
    assert _ids(to_only) == [before.id]


def test_booking_list_filters_by_category_provider_and_client(
    admin_client: APIClient, room: Resource, table: Resource, manager: User, client_user: User
) -> None:
    """Функция, проверяющая фильтры по виду ресурса, менеджеру ресурса и клиенту"""

    other = User.objects.create_user(username="other")
    in_room = _book(resource=room, user=client_user, start=_at(1, 10), end=_at(1, 12))
    at_table = _book(resource=table, user=other, start=_at(1, 10), end=_at(1, 12))

    by_category = admin_client.get(reverse("admin-booking-list"), {"category": "RESTAURANT_TABLE"})
    by_provider = admin_client.get(reverse("admin-booking-list"), {"provider": manager.id})
    by_client = admin_client.get(reverse("admin-booking-list"), {"client": other.id})

    assert _ids(by_category) == [at_table.id]
    assert _ids(by_provider) == [in_room.id]
    assert _ids(by_client) == [at_table.id]


def test_booking_list_orders_by_creation_and_start(
    admin_client: APIClient, room: Resource, client_user: User
) -> None:
    """Функция, проверяющая сортировку по времени создания и по началу брони"""

    late = _book(resource=room, user=client_user, start=_at(9, 10), end=_at(9, 12))
    early = _book(resource=room, user=client_user, start=_at(1, 10), end=_at(1, 12))

    default = admin_client.get(reverse("admin-booking-list"))
    oldest_first = admin_client.get(reverse("admin-booking-list"), {"ordering": "created_at"})
    by_start = admin_client.get(reverse("admin-booking-list"), {"ordering": "start_at"})
    by_start_desc = admin_client.get(reverse("admin-booking-list"), {"ordering": "-start_at"})

    assert _ids(default) == [early.id, late.id]
    assert _ids(oldest_first) == [late.id, early.id]
    assert _ids(by_start) == [early.id, late.id]
    assert _ids(by_start_desc) == [late.id, early.id]


@pytest.mark.parametrize(
    "params",
    [
        {"status": "UNKNOWN"},
        {"category": "SPACESHIP"},
        {"date_from": "not-a-date"},
        {"date_from": "2026-12-05", "date_to": "2026-12-01"},
        {"provider": "abc"},
        {"client": "0"},
        {"ordering": "guests"},
        {"page": "0"},
        {"page_size": "101"},
    ],
)
def test_booking_list_validates_query_parameters(admin_client: APIClient, params: dict) -> None:
    """Функция, проверяющая ошибку проверки данных для неверных параметров запроса"""

    response = admin_client.get(reverse("admin-booking-list"), params)

    assert response.status_code == 400
    assert response.data["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_booking_list_is_read_only(admin_client: APIClient, method: str) -> None:
    """Функция, проверяющая, что список броней нельзя изменить через API"""

    response = getattr(admin_client, method)(reverse("admin-booking-list"), {})

    assert response.status_code == 405
    assert response.data["code"] == "METHOD_NOT_ALLOWED"


@pytest.mark.parametrize("role", [Role.CLIENT, Role.MANAGER])
def test_booking_list_rejects_non_admin_roles(role: str) -> None:
    """Функция, проверяющая запрет доступа клиенту и менеджеру"""

    client = APIClient()
    client.force_authenticate(user=User.objects.create_user(username=f"user-{role}", role=role))

    response = client.get(reverse("admin-booking-list"))

    assert response.status_code == 403
    assert response.data["code"] == "ACCESS_DENIED"


def test_booking_list_rejects_anonymous_and_inactive_admin(admin_user: User) -> None:
    """Функция, проверяющая запрет доступа без входа и для заблокированного администратора"""

    anonymous_response = APIClient().get(reverse("admin-booking-list"))
    admin_user.is_active = False
    admin_user.save()
    client = APIClient()
    client.force_authenticate(user=admin_user)
    inactive_response = client.get(reverse("admin-booking-list"))

    assert anonymous_response.status_code in (401, 403)
    assert inactive_response.status_code == 403
