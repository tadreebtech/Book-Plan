import pytest
from django.contrib.auth.models import Permission

from apps.bookings.models import Resource

pytestmark = pytest.mark.django_db

CHANGELIST_URL = "/admin/bookings/resource/"


def run_action(client, action, *resources):
    return client.post(
        CHANGELIST_URL,
        {"action": action, "_selected_action": [resource.pk for resource in resources]},
        follow=True,
    )


def test_deactivate_and_activate_actions(admin_client, resource):
    response = run_action(admin_client, "deactivate_resources", resource)
    resource.refresh_from_db()
    assert resource.is_active is False
    assert "Ресурсов деактивировано: 1" in [str(m) for m in response.context["messages"]]

    run_action(admin_client, "activate_resources", resource)
    resource.refresh_from_db()
    assert resource.is_active is True


def test_actions_require_change_permission(client, django_user_model, resource):
    staff = django_user_model.objects.create_user(
        username="viewer", password="test-pass-789", is_staff=True
    )
    staff.user_permissions.add(Permission.objects.get(codename="view_resource"))
    client.force_login(staff)

    response = client.get(CHANGELIST_URL)
    assert response.status_code == 200
    assert "deactivate_resources" not in response.text

    run_action(client, "deactivate_resources", resource)
    assert Resource.objects.get(pk=resource.pk).is_active is True
