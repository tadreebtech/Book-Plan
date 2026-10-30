from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User

pytestmark = pytest.mark.django_db


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


def test_user_list_returns_basic_fields(admin_client: APIClient) -> None:
    """Функция, проверяющая состав ответа и отсутствие чувствительных полей"""

    User.objects.create_user(username="client", email="client@example.com", role=Role.CLIENT)

    response = admin_client.get(reverse("admin-user-list"))

    assert response.status_code == 200
    assert response.data["count"] == 2
    assert response["Content-Type"].startswith("application/json")
    assert response.json()["count"] == 2
    assert response.data["page"] == 1
    assert response.data["page_size"] == 20
    assert len(response.data["results"]) == 2
    assert set(response.data["results"][0]) == {
        "id",
        "email",
        "name",
        "role",
        "is_active",
        "created_at",
    }


def test_user_list_defaults_to_twenty_results(admin_client: APIClient) -> None:
    """Функция, проверяющая ограничение первой страницы двадцатью пользователями"""

    for index in range(21):
        User.objects.create_user(username=f"user-{index}")

    response = admin_client.get(reverse("admin-user-list"))

    assert response.status_code == 200
    assert response.data["count"] == 22
    assert len(response.data["results"]) == 20


def test_user_list_paginates_without_duplicates(admin_client: APIClient) -> None:
    """Функция, проверяющая размер страниц, общее количество и устойчивый порядок"""

    for index in range(5):
        User.objects.create_user(username=f"user-{index}", email=f"user-{index}@example.com")

    first = admin_client.get(reverse("admin-user-list"), {"page": 1, "page_size": 2})
    second = admin_client.get(reverse("admin-user-list"), {"page": 2, "page_size": 2})
    beyond = admin_client.get(reverse("admin-user-list"), {"page": 5, "page_size": 2})

    assert first.data["count"] == second.data["count"] == beyond.data["count"] == 6
    assert len(first.data["results"]) == len(second.data["results"]) == 2
    assert {user["id"] for user in first.data["results"]}.isdisjoint(
        {user["id"] for user in second.data["results"]}
    )
    assert beyond.data["results"] == []


def test_user_list_handles_a_very_large_page(admin_client: APIClient) -> None:
    """Функция, проверяющая ответ для номера страницы за пределами размера базы данных"""

    response = admin_client.get(reverse("admin-user-list"), {"page": "9" * 30})

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"] == []


def test_user_list_searches_email_and_full_name(admin_client: APIClient) -> None:
    """Функция, проверяющая поиск по части email и полного имени без учёта регистра"""

    matched = User.objects.create_user(
        username="person", email="person@example.com", first_name="Анна", last_name="Петрова"
    )

    by_email = admin_client.get(reverse("admin-user-list"), {"search": "PERSON@EXAMPLE"})
    by_name = admin_client.get(reverse("admin-user-list"), {"search": "анна петр"})

    assert [user["id"] for user in by_email.data["results"]] == [matched.id]
    assert [user["id"] for user in by_name.data["results"]] == [matched.id]
    assert by_name.data["results"][0]["name"] == "Анна Петрова"


def test_user_list_searches_username_and_uses_it_as_a_name(admin_client: APIClient) -> None:
    """Функция, проверяющая поиск по логину и имя при пустых полях профиля"""

    matched = User.objects.create_user(username="find-me")

    response = admin_client.get(reverse("admin-user-list"), {"search": "FIND-ME"})

    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == matched.id
    assert response.data["results"][0]["name"] == "find-me"


def test_user_list_combines_role_status_and_search(admin_client: APIClient) -> None:
    """Функция, проверяющая совместную работу фильтров и поиска"""

    matched = User.objects.create_user(
        username="manager-one",
        email="manager@example.com",
        role=Role.MANAGER,
        is_active=False,
    )
    User.objects.create_user(username="manager-two", email="other@example.com", role=Role.MANAGER)
    User.objects.create_user(
        username="client-one", email="manager-client@example.com", role=Role.CLIENT
    )

    response = admin_client.get(
        reverse("admin-user-list"),
        {"role": "Provider", "is_active": "false", "search": "manager"},
    )

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert [user["id"] for user in response.data["results"]] == [matched.id]
    assert response.data["results"][0]["role"] == Role.MANAGER


@pytest.mark.parametrize("role", [Role.CLIENT, Role.MANAGER, Role.ADMIN])
def test_user_list_filters_each_stored_role(admin_client: APIClient, role: str) -> None:
    """Функция, проверяющая фильтр для каждой роли, существующей в модели"""

    if role != Role.ADMIN:
        User.objects.create_user(username=f"user-{role}", role=role)

    response = admin_client.get(reverse("admin-user-list"), {"role": role})

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert all(user["role"] == role for user in response.data["results"])


def test_user_list_filters_active_users(admin_client: APIClient) -> None:
    """Функция, проверяющая фильтр активных пользователей отдельно от других условий"""

    User.objects.create_user(username="inactive", is_active=False)

    response = admin_client.get(reverse("admin-user-list"), {"is_active": "true"})

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert all(user["is_active"] for user in response.data["results"])


def test_user_list_orders_by_registration_date_and_email(admin_client: APIClient) -> None:
    """Функция, проверяющая сортировку по дате регистрации и email"""

    older = User.objects.create_user(username="older", email="z@example.com")
    newer = User.objects.create_user(username="newer", email="beta@example.com")
    now = timezone.now()
    User.objects.filter(pk=older.pk).update(created_at=now - timedelta(days=2))
    User.objects.filter(pk=newer.pk).update(created_at=now + timedelta(days=2))

    by_date = admin_client.get(reverse("admin-user-list"))
    by_date_ascending = admin_client.get(reverse("admin-user-list"), {"ordering": "created_at"})
    by_email = admin_client.get(reverse("admin-user-list"), {"ordering": "email"})
    by_email_descending = admin_client.get(reverse("admin-user-list"), {"ordering": "-email"})

    assert by_date.data["results"][0]["id"] == newer.id
    assert by_date.data["results"][-1]["id"] == older.id
    assert by_date_ascending.data["results"][0]["id"] == older.id
    assert by_date_ascending.data["results"][-1]["id"] == newer.id
    assert [user["email"] for user in by_email.data["results"]] == [
        "admin@example.com",
        "beta@example.com",
        "z@example.com",
    ]
    assert [user["email"] for user in by_email_descending.data["results"]] == [
        "z@example.com",
        "beta@example.com",
        "admin@example.com",
    ]


@pytest.mark.parametrize("role", [Role.CLIENT, Role.MANAGER])
def test_user_list_rejects_non_admin_roles(role: str, admin_user: User) -> None:
    """Функция, проверяющая запрет доступа клиенту и менеджеру"""

    user = User.objects.create_user(username=f"user-{role}", role=role)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("admin-user-list"))

    assert response.status_code == 403
    assert response.data == {
        "code": "ACCESS_DENIED",
        "message": "Недостаточно прав для выполнения операции.",
        "details": {},
    }


def test_user_list_rejects_anonymous_and_inactive_admin(admin_user: User) -> None:
    """Функция, проверяющая запрет доступа без входа и после деактивации администратора"""

    anonymous_response = APIClient().get(reverse("admin-user-list"))
    admin_user.is_active = False
    admin_user.save(update_fields=["is_active"])
    client = APIClient()
    client.force_authenticate(user=admin_user)
    inactive_response = client.get(reverse("admin-user-list"))

    assert anonymous_response.status_code in (401, 403)
    assert anonymous_response.data["code"] == "UNAUTHORIZED"
    assert inactive_response.status_code == 403
    assert inactive_response.data["code"] == "ACCESS_DENIED"


def test_user_list_accepts_a_real_admin_session(admin_user: User) -> None:
    """Функция, проверяющая доступ администратора через обычный вход в систему"""

    client = APIClient()

    assert client.login(username=admin_user.username, password="test-pass")
    assert client.get(reverse("admin-user-list")).status_code == 200


def test_user_list_rejects_post_with_api_error_format(admin_client: APIClient) -> None:
    """Функция, проверяющая запрет неподдерживаемого метода и формат ошибки"""

    response = admin_client.post(reverse("admin-user-list"), {})

    assert response.status_code == 405
    assert response.data == {
        "code": "METHOD_NOT_ALLOWED",
        "message": "Метод запроса не поддерживается.",
        "details": {},
    }


def test_user_list_hides_unexpected_errors(
    admin_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Функция, проверяющая формат ответа при непредвиденной ошибке выборки"""

    def fail_selector(**kwargs: object) -> None:
        """Функция, имитирующая непредвиденную ошибку без обращения к базе данных"""

        raise RuntimeError("sensitive-value")

    monkeypatch.setattr("apps.accounts.apis.user_list", fail_selector)

    response = admin_client.get(reverse("admin-user-list"))

    assert response.status_code == 500
    assert response.data == {
        "code": "INTERNAL_ERROR",
        "message": "Внутренняя ошибка сервера.",
        "details": {},
    }
    assert "sensitive-value" not in str(response.json())
    assert "sensitive-value" not in caplog.text


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"page": 0}, "page"),
        ({"page_size": 0}, "page_size"),
        ({"page_size": 101}, "page_size"),
        ({"search": "x" * 151}, "search"),
        ({"role": "unknown"}, "role"),
        ({"is_active": "unknown"}, "is_active"),
        ({"ordering": "username"}, "ordering"),
    ],
)
def test_user_list_validates_query_parameters(
    admin_client: APIClient, params: dict[str, object], field: str
) -> None:
    """Функция, проверяющая единый формат ошибок для неверных параметров"""

    response = admin_client.get(reverse("admin-user-list"), params)

    assert response.status_code == 400
    assert response.data["code"] == "VALIDATION_ERROR"
    assert response.data["message"] == "Некорректные параметры запроса."
    assert field in response.data["details"]
