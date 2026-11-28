from datetime import timedelta

import pytest
from django.contrib.admin import helpers
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.bookings.models import (
    Booking,
    BookingStatus,
    Resource,
    ResourceActivationAction,
    ResourceActivationLog,
    ResourceKind,
)

pytestmark = pytest.mark.django_db

CHANGELIST = "admin:bookings_resource_changelist"


@pytest.fixture
def admin_user() -> User:
    """Функция, создающая администратора платформы с доступом в админку"""

    return User.objects.create_user(
        username="admin", role=Role.ADMIN, is_staff=True, is_superuser=True
    )


@pytest.fixture
def resource() -> Resource:
    """Функция, создающая активный ресурс"""

    return Resource.objects.create(name="Room 101", kind=ResourceKind.UNIVERSITY_ROOM, capacity=4)


def _client(user: User) -> Client:
    """Функция, возвращающая клиент админки, вошедший от имени user"""

    client = Client()
    client.force_login(user)
    return client


def _run_action(user: User, action: str, resources: list[Resource], confirm: bool):
    """Функция, запускающая действие над ресурсами из списка в админке"""

    data = {
        "action": action,
        helpers.ACTION_CHECKBOX_NAME: [str(r.pk) for r in resources],
    }
    if confirm:
        data["post"] = "yes"
    return _client(user).post(reverse(CHANGELIST), data)


def _booking(resource: Resource, *, days: int, status: str = BookingStatus.CONFIRMED) -> Booking:
    """Функция, создающая бронь ресурса через days дней"""

    client = User.objects.create_user(username=f"client{Booking.objects.count()}")
    start = timezone.now() + timedelta(days=days)
    return Booking.objects.create(
        resource=resource,
        user=client,
        start_at=start,
        end_at=start + timedelta(hours=1),
        guests=1,
        status=status,
    )


def test_changelist_shows_status_and_upcoming_bookings(admin_user: User, resource: Resource):
    """Функция, проверяющая колонки статуса и будущих броней в списке ресурсов"""

    _booking(resource, days=1)
    _booking(resource, days=2, status=BookingStatus.CANCELLED)

    response = _client(admin_user).get(reverse(CHANGELIST))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Будущие брони" in content
    assert "Активировать выбранные ресурсы" in content
    assert "Деактивировать выбранные ресурсы" in content
    assert response.context["cl"].result_list.get(pk=resource.pk).upcoming_bookings_count == 1


def test_deactivate_asks_for_confirmation_first(admin_user: User, resource: Resource):
    """Функция, проверяющая, что деактивация сначала показывает подтверждение"""

    response = _run_action(admin_user, "deactivate_resources", [resource], confirm=False)

    assert response.status_code == 200
    assert "Подтвердите деактивацию" in response.content.decode()
    resource.refresh_from_db()
    assert resource.is_active is True
    assert not ResourceActivationLog.objects.exists()


def test_deactivate_warns_about_existing_bookings(admin_user: User, resource: Resource):
    """Функция, проверяющая предупреждение о действующих бронях на странице подтверждения"""

    _booking(resource, days=1)
    _booking(resource, days=3)

    response = _run_action(admin_user, "deactivate_resources", [resource], confirm=False)

    content = response.content.decode()
    assert 'id="bookings-warning"' in content
    assert "действующие брони (2)" in content


def test_deactivate_without_bookings_has_no_warning(admin_user: User, resource: Resource):
    """Функция, проверяющая, что без броней предупреждение не показывается"""

    _booking(resource, days=-2)

    response = _run_action(admin_user, "deactivate_resources", [resource], confirm=False)

    assert 'id="bookings-warning"' not in response.content.decode()


def test_confirmed_deactivation_changes_resource_and_keeps_bookings(
    admin_user: User, resource: Resource
):
    """Функция, проверяющая деактивацию после подтверждения с записью в журнал"""

    booking = _booking(resource, days=1)

    response = _run_action(admin_user, "deactivate_resources", [resource], confirm=True)

    assert response.status_code == 302
    resource.refresh_from_db()
    assert resource.is_active is False
    log = ResourceActivationLog.objects.get()
    assert (log.resource_id, log.actor, log.action) == (
        resource.pk,
        admin_user,
        ResourceActivationAction.DEACTIVATED,
    )
    booking.refresh_from_db()
    assert booking.status == BookingStatus.CONFIRMED


def test_confirmed_activation_changes_only_inactive_resources(admin_user: User, resource: Resource):
    """Функция, проверяющая активацию, которая не трогает уже активные ресурсы"""

    inactive = Resource.objects.create(
        name="Table 5", kind=ResourceKind.UNIVERSITY_ROOM, capacity=2, is_active=False
    )

    response = _run_action(admin_user, "activate_resources", [resource, inactive], confirm=True)

    assert response.status_code == 302
    inactive.refresh_from_db()
    assert inactive.is_active is True
    log = ResourceActivationLog.objects.get()
    assert (log.resource_id, log.action) == (inactive.pk, ResourceActivationAction.ACTIVATED)


@pytest.mark.parametrize("role", [Role.MANAGER, Role.CLIENT])
def test_actions_are_hidden_from_non_admin_roles(role: str, resource: Resource):
    """Функция, проверяющая, что сотрудник без роли администратора не видит действий"""

    staff = User.objects.create_user(
        username=f"staff-{role}", role=role, is_staff=True, is_superuser=True
    )

    page = _client(staff).get(reverse(CHANGELIST)).content.decode()
    _run_action(staff, "deactivate_resources", [resource], confirm=True)

    assert "Деактивировать выбранные ресурсы" not in page
    resource.refresh_from_db()
    assert resource.is_active is True
    assert not ResourceActivationLog.objects.exists()
