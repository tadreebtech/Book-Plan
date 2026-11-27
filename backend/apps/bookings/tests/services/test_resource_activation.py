import pytest
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Role, User
from apps.bookings.models import Resource, ResourceActivationLog
from apps.bookings.services import resource_activate, resource_deactivate

pytestmark = pytest.mark.django_db


def test_resource_deactivate_and_activate_round_trip(listing_factory) -> None:
    """Функция, проверяющая обе операции сервиса и две записи в журнале"""

    admin = User.objects.create_user(username="admin", role=Role.ADMIN)
    resource = listing_factory()

    resource_deactivate(actor=admin, resource_id=resource.pk)
    resource = resource_activate(actor=admin, resource_id=resource.pk)

    assert resource.is_active is True
    assert list(ResourceActivationLog.objects.order_by("pk").values_list("action", flat=True)) == [
        "DEACTIVATED",
        "ACTIVATED",
    ]


@pytest.mark.parametrize(
    ("role", "is_active"), [(Role.CLIENT, True), (Role.MANAGER, True), (Role.ADMIN, False)]
)
def test_resource_deactivate_requires_active_admin(
    listing_factory, role: str, is_active: bool
) -> None:
    """Функция, проверяющая, что сервис отказывает всем, кроме активного администратора"""

    actor = User.objects.create_user(username="actor", role=role, is_active=is_active)
    resource = listing_factory()

    with pytest.raises(PermissionDenied):
        resource_deactivate(actor=actor, resource_id=resource.pk)

    resource.refresh_from_db()
    assert resource.is_active is True


def test_resource_deactivate_raises_for_missing_resource() -> None:
    """Функция, проверяющая ошибку для несуществующего ресурса"""

    admin = User.objects.create_user(username="admin", role=Role.ADMIN)

    with pytest.raises(Resource.DoesNotExist):
        resource_deactivate(actor=admin, resource_id=999999)
