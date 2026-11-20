import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.bookings.models import Reference, Resource, ResourceKind, ResourceStatus

pytestmark = pytest.mark.django_db
URL = "/api/v1/admin/references/"


@pytest.fixture
def admin_client() -> APIClient:
    """Функция, создающая клиент администратора для проверки справочников"""

    client = APIClient()
    client.force_authenticate(user=User.objects.create_user(username="admin", role=Role.ADMIN))
    return client


@pytest.fixture
def reference() -> Reference:
    """Функция, создающая значение справочника"""

    return Reference.objects.create(type="location_type", value="Conference room")


def test_reference_crud_and_partial_update(admin_client: APIClient) -> None:
    """Функция, проверяющая создание, список, изменение и удаление справочника"""

    created = admin_client.post(
        URL, {"type": "equipment_unit", "value": "Projector"}, format="json"
    )
    assert created.status_code == 201
    assert created.data == {
        "id": created.data["id"],
        "type": "equipment_unit",
        "value": "Projector",
        "is_active": True,
    }
    detail = f"{URL}{created.data['id']}/"
    assert admin_client.get(URL).data["results"] == [created.data]

    changed = admin_client.patch(detail, {"value": "Display"}, format="json")
    assert changed.status_code == 200
    assert changed.data["value"] == "Display"
    assert changed.data["type"] == "equipment_unit"
    assert changed.data["is_active"] is True
    renamed = admin_client.patch(detail, {"type": "equipment_type"}, format="json")
    assert renamed.status_code == 200
    assert renamed.data["type"] == "equipment_type"
    deleted = admin_client.delete(detail)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert not Reference.objects.exists()


def test_reference_list_filters_by_type(admin_client: APIClient, reference: Reference) -> None:
    """Функция, проверяющая фильтрацию разных справочников и пагинацию"""

    Reference.objects.create(type="equipment_unit", value=reference.value)
    Reference.objects.create(type=reference.type, value="Workshop", is_active=False)

    response = admin_client.get(URL, {"type": reference.type, "page_size": 1, "page": 2})

    assert response.status_code == 200
    assert response.data["count"] == 2
    assert response.data["results"][0]["value"] == "Workshop"
    assert response.data["results"][0]["is_active"] is False
    assert admin_client.get(URL, {"type": "missing"}).data["results"] == []
    assert admin_client.get(URL, {"page": 10**30}).data["results"] == []


def test_used_reference_requires_deactivation(
    admin_client: APIClient, reference: Reference
) -> None:
    """Функция, проверяющая защиту используемого значения и сохранность его связей"""

    resource = Resource.objects.create(
        name="Archived room",
        kind=ResourceKind.HOTEL_ROOM,
        capacity=2,
        status=ResourceStatus.ARCHIVED,
        is_active=False,
    )
    resource.references.add(reference)
    detail = f"{URL}{reference.pk}/"

    blocked = admin_client.delete(detail)
    assert blocked.status_code == 409
    assert blocked.data["code"] == "REFERENCE_IN_USE"
    assert set(blocked.data) == {"code", "message", "details"}
    deactivated = admin_client.patch(detail, {"is_active": False}, format="json")
    assert deactivated.status_code == 200
    assert deactivated.data["is_active"] is False
    assert list(resource.references.all()) == [reference]
    assert admin_client.delete(detail).status_code == 409

    resource.references.clear()
    assert admin_client.delete(detail).status_code == 204
    assert Resource.objects.filter(pk=resource.pk).exists()


@pytest.mark.parametrize(
    "fields",
    [
        None,
        {"role": Role.CLIENT, "is_staff": True},
        {"role": Role.MANAGER},
        {"role": Role.ADMIN, "is_active": False},
    ],
)
@pytest.mark.parametrize("method", ["list", "create", "patch", "delete"])
def test_reference_operations_require_active_admin(
    fields: dict | None, method: str, reference: Reference
) -> None:
    """Функция, проверяющая права на все операции со справочниками"""

    client = APIClient()
    if fields is not None:
        client.force_authenticate(user=User.objects.create_user(username="denied", **fields))
    operations = {
        "list": lambda: client.get(URL),
        "create": lambda: client.post(URL, {"type": "unit", "value": "Other"}, format="json"),
        "patch": lambda: client.patch(f"{URL}{reference.pk}/", {"is_active": False}, format="json"),
        "delete": lambda: client.delete(f"{URL}{reference.pk}/"),
    }

    response = operations[method]()

    assert response.status_code == 403
    assert response.data["code"] == ("UNAUTHORIZED" if fields is None else "ACCESS_DENIED")
    assert set(response.data) == {"code", "message", "details"}
    reference.refresh_from_db()
    assert reference.is_active is True
    assert Reference.objects.count() == 1


@pytest.mark.parametrize("payload", [{"type": "", "value": "X"}, {"type": "unit", "value": ""}])
def test_reference_rejects_blank_properties(admin_client: APIClient, payload: dict) -> None:
    """Функция, проверяющая валидацию свойств справочника"""

    response = admin_client.post(URL, payload, format="json")

    assert response.status_code == 400
    assert response.data["code"] == "VALIDATION_ERROR"
    assert set(response.data) == {"code", "message", "details"}
    assert not Reference.objects.exists()


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_reference_missing_and_invalid_id(admin_client: APIClient, method: str) -> None:
    """Функция, проверяющая ошибки отсутствующего и некорректного идентификатора"""

    missing = getattr(admin_client, method)(f"{URL}999999/")
    invalid = getattr(admin_client, method)(f"{URL}abc/")

    assert missing.status_code == 404
    assert missing.data["code"] == "NOT_FOUND"
    assert invalid.status_code == 400
    assert invalid.data["code"] == "VALIDATION_ERROR"
