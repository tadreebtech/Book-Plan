import pytest

from apps.bookings.models import Resource
from apps.bookings.services import resource_set_active

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("is_active", [False, True])
def test_resource_set_active_saves_state(resource, is_active):
    Resource.objects.filter(pk=resource.pk).update(is_active=not is_active)
    resource.refresh_from_db()

    resource_set_active(resource=resource, is_active=is_active)

    resource.refresh_from_db()
    assert resource.is_active is is_active
