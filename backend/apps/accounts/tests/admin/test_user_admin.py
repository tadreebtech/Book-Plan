from typing import Any

import pytest
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.exceptions import SelfAdminDemotionForbidden
from apps.accounts.models import AuditAction, AuditLog, Role, User

pytestmark = pytest.mark.django_db


def change_form_data(user: User, **overrides: Any) -> dict[str, Any]:
    """Функция, собирающая данные формы изменения пользователя в админке"""

    data: dict[str, Any] = {
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "date_joined_0": user.date_joined.strftime("%Y-%m-%d"),
        "date_joined_1": user.date_joined.strftime("%H:%M:%S"),
        "last_login_0": "",
        "last_login_1": "",
        "role": user.role,
    }
    for flag in ("is_active", "is_staff", "is_superuser"):
        if getattr(user, flag):
            data[flag] = "on"
    data.update(overrides)
    return data


def post_change(actor: User, target: User, **overrides: Any) -> Any:
    """Функция, отправляющая форму изменения пользователя в админку от имени actor"""

    client = Client()
    client.force_login(actor)
    url = reverse("admin:accounts_user_change", args=[target.pk])
    return client.post(url, change_form_data(target, **overrides))


@pytest.fixture
def admin_user() -> User:
    """Функция, создающая администратора для работы в админке"""

    return User.objects.create_user(
        username="admin", role=Role.ADMIN, is_staff=True, is_superuser=True
    )


def test_admin_role_change_is_saved_with_audit(admin_user: User) -> None:
    """Функция, проверяющая смену роли в админке с записью в аудит"""

    target = User.objects.create_user(username="target", role=Role.CLIENT)

    response = post_change(admin_user, target, role=Role.MANAGER, first_name="New")

    assert response.status_code == 302
    target.refresh_from_db()
    assert target.role == Role.MANAGER
    assert target.first_name == "New"
    audit_log = AuditLog.objects.get()
    assert audit_log.action == AuditAction.CHANGE_ROLE
    assert (audit_log.old_value, audit_log.new_value) == (Role.CLIENT, Role.MANAGER)


def get_change_form(actor: User, target: User) -> Any:
    """Функция, открывающая форму изменения пользователя в админке от имени actor"""

    client = Client()
    client.force_login(actor)
    response = client.get(reverse("admin:accounts_user_change", args=[target.pk]))
    return response.context["adminform"].form


def test_admin_sees_editable_role_of_other_user(admin_user: User) -> None:
    """Функция, проверяющая, что администратор может править роль другого пользователя"""

    target = User.objects.create_user(username="target", role=Role.CLIENT)

    assert "role" in get_change_form(admin_user, target).fields


def test_admin_cannot_remove_own_admin_role(admin_user: User) -> None:
    """Функция, проверяющая, что роль администратора у самого себя доступна только для чтения"""

    group = Group.objects.create(name="editors")

    assert "role" not in get_change_form(admin_user, admin_user).fields

    response = post_change(
        admin_user, admin_user, role=Role.CLIENT, first_name="New", groups=[group.pk]
    )

    assert response.status_code == 302
    admin_user.refresh_from_db()
    assert admin_user.role == Role.ADMIN
    assert admin_user.first_name == "New"
    assert admin_user.groups.get() == group
    assert AuditLog.objects.count() == 0


@pytest.mark.parametrize("staff_role", [Role.CLIENT, Role.MANAGER])
def test_non_admin_cannot_change_role(staff_role: str) -> None:
    """Функция, проверяющая, что сотрудник без роли администратора не меняет роль"""

    staff = User.objects.create_user(
        username="staff", role=staff_role, is_staff=True, is_superuser=True
    )

    assert "role" not in get_change_form(staff, staff).fields

    target = User.objects.create_user(username="target", role=Role.CLIENT)

    response = post_change(staff, target, role=Role.ADMIN, first_name="New")

    assert response.status_code == 302
    target.refresh_from_db()
    assert target.role == Role.CLIENT
    assert target.first_name == "New"
    assert AuditLog.objects.count() == 0


def test_role_change_rejected_by_service_rolls_back_all_changes(
    admin_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Функция, проверяющая откат всех изменений формы, если сервис отклонил смену роли"""

    def reject_role_change(**kwargs: Any) -> User:
        raise SelfAdminDemotionForbidden()

    monkeypatch.setattr("apps.accounts.admin.user_role_change", reject_role_change)
    target = User.objects.create_user(username="target", role=Role.CLIENT)
    group = Group.objects.create(name="editors")

    response = post_change(
        admin_user, target, role=Role.MANAGER, first_name="New", groups=[group.pk]
    )

    assert response.status_code == 403
    target.refresh_from_db()
    assert target.role == Role.CLIENT
    assert target.first_name == ""
    assert not target.groups.exists()
    assert AuditLog.objects.count() == 0
    assert LogEntry.objects.count() == 0
