import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.bookings.models import Category, Resource, ResourceKind

pytestmark = pytest.mark.django_db
URL = "/api/v1/admin/categories/"


@pytest.fixture
def admin_client() -> APIClient:
    """Функция, создающая клиент активного администратора"""

    client = APIClient()
    client.force_authenticate(user=User.objects.create_user(username="admin", role=Role.ADMIN))
    return client


@pytest.fixture
def category() -> Category:
    """Функция, создающая категорию для проверки API"""

    return Category.objects.create(name="Rooms", slug="rooms", description="Book a room")


def test_category_crud(admin_client: APIClient) -> None:
    """Функция, проверяющая создание, список, карточку, изменение и удаление категории"""

    created = admin_client.post(URL, {"name": "Rooms", "slug": "rooms"}, format="json")
    assert created.status_code == 201
    assert created.json() == {
        "id": created.data["id"],
        "name": "Rooms",
        "slug": "rooms",
        "description": "",
        "is_active": True,
    }
    detail = f"{URL}{created.data['id']}/"
    assert admin_client.get(URL).data["results"] == [created.data]
    assert admin_client.get(detail).data == created.data

    changed = admin_client.patch(detail, {"description": "New description"}, format="json")
    assert changed.status_code == 200
    assert changed.data["description"] == "New description"
    assert changed.data["slug"] == "rooms"
    assert changed.data["is_active"] is True

    deleted = admin_client.delete(detail)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert admin_client.get(detail).status_code == 404


def test_category_duplicate_slug_is_rejected_on_create_and_update(
    admin_client: APIClient, category: Category
) -> None:
    """Функция, проверяющая уникальность slug и сохранность данных при ошибке изменения"""

    other = Category.objects.create(name="Tables", slug="tables")
    created = admin_client.post(URL, {"name": "Duplicate", "slug": category.slug}, format="json")
    changed = admin_client.patch(
        f"{URL}{other.pk}/", {"name": "Changed", "slug": category.slug}, format="json"
    )
    for response in (created, changed):
        assert response.status_code == 400
        assert response.data["code"] == "VALIDATION_ERROR"
        assert set(response.data) == {"code", "message", "details"}
        assert "slug" in response.data["details"]
    other.refresh_from_db()
    assert other.name == "Tables"
    assert other.slug == "tables"


@pytest.mark.parametrize("slug", ["bad slug", "bad/slug", "категория", "", "x" * 256])
def test_category_rejects_invalid_slug(admin_client: APIClient, slug: str) -> None:
    """Функция, проверяющая формат slug"""

    response = admin_client.post(URL, {"name": "Rooms", "slug": slug}, format="json")

    assert response.status_code == 400
    assert response.data["code"] == "VALIDATION_ERROR"
    assert "slug" in response.data["details"]
    assert not Category.objects.exists()


def test_category_search_and_pagination(admin_client: APIClient) -> None:
    """Функция, проверяющая поиск, количество результатов и страницы категорий"""

    first = Category.objects.create(name="Аудитория 1", slug="room-1")
    second = Category.objects.create(name="Аудитория 2", slug="room-2")
    Category.objects.create(name="Table", slug="table")

    page = admin_client.get(URL, {"search": "АУДИТОРИЯ", "page_size": 1, "page": 2})
    assert page.status_code == 200
    assert page.data["count"] == 2
    assert [row["id"] for row in page.data["results"]] == [second.pk]
    by_slug = admin_client.get(URL, {"search": "ROOM-1"})
    assert [row["id"] for row in by_slug.data["results"]] == [first.pk]
    assert admin_client.get(URL, {"page": 10**30}).data["results"] == []


@pytest.mark.parametrize(
    "fields",
    [
        None,
        {"role": Role.CLIENT, "is_staff": True},
        {"role": Role.MANAGER},
        {"role": Role.ADMIN, "is_active": False},
    ],
)
@pytest.mark.parametrize("method", ["list", "create", "get", "patch", "delete"])
def test_category_operations_require_active_admin(
    fields: dict | None, method: str, category: Category
) -> None:
    """Функция, проверяющая права на все операции с категориями"""

    client = APIClient()
    if fields is not None:
        client.force_authenticate(user=User.objects.create_user(username="denied", **fields))
    operations = {
        "list": lambda: client.get(URL),
        "create": lambda: client.post(URL, {"name": "Other", "slug": "other"}, format="json"),
        "get": lambda: client.get(f"{URL}{category.pk}/"),
        "patch": lambda: client.patch(f"{URL}{category.pk}/", {"is_active": False}, format="json"),
        "delete": lambda: client.delete(f"{URL}{category.pk}/"),
    }
    response = operations[method]()

    assert response.status_code == 403
    assert response.data["code"] == ("UNAUTHORIZED" if fields is None else "ACCESS_DENIED")
    assert set(response.data) == {"code", "message", "details"}
    category.refresh_from_db()
    assert category.is_active is True
    assert Category.objects.count() == 1


def test_category_in_use_can_be_deactivated(admin_client: APIClient, category: Category) -> None:
    """Функция, проверяющая отказ удаления используемой категории и возможность деактивации"""

    resource = Resource.objects.create(
        name="Room", kind=ResourceKind.HOTEL_ROOM, capacity=2, category=category
    )
    response = admin_client.delete(f"{URL}{category.pk}/")
    assert response.status_code == 409
    assert response.data["code"] == "CATEGORY_IN_USE"
    assert "1" in response.data["message"]
    assert (
        admin_client.patch(f"{URL}{category.pk}/", {"is_active": False}, format="json").status_code
        == 200
    )
    resource.refresh_from_db()
    assert resource.category_id == category.pk


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_category_missing_or_invalid_id(admin_client: APIClient, method: str) -> None:
    """Функция, проверяющая единый формат ошибок идентификатора"""

    missing = getattr(admin_client, method)(f"{URL}999999/")
    invalid = getattr(admin_client, method)(f"{URL}abc/")

    assert missing.status_code == 404
    assert missing.data["code"] == "NOT_FOUND"
    assert invalid.status_code == 400
    assert invalid.data["code"] == "VALIDATION_ERROR"
